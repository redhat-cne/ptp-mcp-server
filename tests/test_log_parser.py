"""Cluster-free unit tests for PTPLogParser.

These tests exercise the log parser directly on representative raw log lines.
They never touch a live cluster or the `oc` binary — only the pure
parsing/classification methods are called. Each test embeds the raw line it
parses inline, so the input under test is visible next to its assertions.

Covers CNF-26712:
  * log-severity classifier (error/warning/info)
  * ptp4l rms/max summary-line fields
  * regression: previously-parsed fields still parse
  * PR #8 servo-line fields are consumed unchanged (not re-implemented)
"""

import pytest


# --- Severity classifier -------------------------------------------------

@pytest.mark.parametrize("line", [
    "ptp4l[1.2]: [cfg] port 1: fault detected",
    "ptp4l[1.2]: [cfg] Lost connection to peer",
    "ptp4l[1.2]: [cfg] timed out while polling for tx timestamp",
    "phc2sys[1.2]: [cfg] failed to open /dev/ptp0",
])
def test_severity_classifier_labels_error_lines(parser, line):
    assert parser._classify_severity(line) == "error"


@pytest.mark.parametrize("line", [
    "ptp4l[1.2]: [cfg] clockcheck: clock jumped backwards",
    "dpll[1]:[cfg] decision: Status 3, Offset 9, In spec false, "
    "Source GNSS lost false, On holdover false",
    "dpll[1]:[cfg] entering holdover",
])
def test_severity_classifier_labels_warning_lines(parser, line):
    assert parser._classify_severity(line) == "warning"


def test_severity_classifier_normal_servo_line_is_info(parser):
    # Normal ptp4l servo line (locked, s2) — the healthy steady-state case.
    servo_line = ("ptp4l[123.456]: [ptp4l.0.config] master offset -5 s2 "
                  "freq +1234 path delay 456")
    assert parser._classify_severity(servo_line) == "info"


def test_healthy_dpll_decision_line_is_info(parser):
    # A routine, healthy DPLL decision line — in spec, not on holdover. It
    # contains the substring "holdover" ("On holdover false"), so it guards
    # against a bare-substring severity marker mis-classifying it as warning:
    # the markers are anchored so routine decision lines stay info (regression
    # for the bare "holdover" / "not in spec" false positives).
    healthy_dpll_decision_line = (
        "dpll[123]:[ptp4l.0.config] decision: Status 3, Offset 5, "
        "In spec true, Source GNSS lost false, On holdover false")
    assert parser._classify_severity(healthy_dpll_decision_line) == "info"
    assert parser._parse_log_line(healthy_dpll_decision_line).level == "info"


def test_out_of_spec_dpll_decision_line_is_warning(parser):
    # A DPLL decision line reporting an out-of-spec ("In spec false") clock:
    # "In spec false" and "On holdover true" are genuine warning conditions.
    out_of_spec_dpll_decision_line = (
        "dpll[123]:[ptp4l.0.config] decision: Status 3, Offset 9999, "
        "In spec false, Source GNSS lost false, On holdover true")
    assert parser._classify_severity(out_of_spec_dpll_decision_line) == "warning"


def test_error_marker_wins_over_warning_marker(parser):
    # A line containing both a warning and an error marker classifies as error
    # (error patterns are checked first).
    line = "ptp4l[1.2]: [cfg] clockcheck failed: fault on port 1"
    assert parser._classify_severity(line) == "error"


def test_register_severity_pattern_extends_table(parser):
    assert parser._classify_severity("some custom marker line") == "info"
    parser.register_severity_pattern(r"custom marker", "warning")
    assert parser._classify_severity("some custom marker line") == "warning"


def test_parse_log_line_sets_level_from_classifier(parser):
    # _parse_log_line no longer hard-codes level="info"; error markers surface.
    fault_line = ("ptp4l[123.456]: [ptp4l.0.config] port 1: fault detected "
                  "on interface")
    timeout_line = ("ptp4l[123.456]: [ptp4l.0.config] timed out while polling "
                    "for tx timestamp")
    servo_line = ("ptp4l[123.456]: [ptp4l.0.config] master offset -5 s2 "
                  "freq +1234 path delay 456")
    assert parser._parse_log_line(fault_line).level == "error"
    assert parser._parse_log_line(timeout_line).level == "error"
    assert parser._parse_log_line(servo_line).level == "info"


def test_error_level_flows_through_parse_log_line(parser):
    # Demonstrates that check_ptp_health's error_count/warning_count (which count
    # LogEntry.level == "error"/"warning") would now be non-zero.
    fault_line = ("ptp4l[123.456]: [ptp4l.0.config] port 1: fault detected "
                  "on interface")
    clockcheck_line = ("ptp4l[123.456]: [ptp4l.0.config] clockcheck: clock "
                       "jumped backwards")
    entries = [parser._parse_log_line(fault_line),
               parser._parse_log_line(clockcheck_line)]
    assert sum(1 for e in entries if e.level == "error") == 1
    assert sum(1 for e in entries if e.level == "warning") == 1


# --- rms/max summary-line fields ----------------------------------------

def test_rms_summary_line_parsed(parser):
    parsed = parser._parse_ptp4l_message(
        "rms 5 max 12 freq +1234 +/- 56 delay 700 +/- 8"
    )
    assert parsed["rms"] == 5
    assert parsed["max_offset"] == 12
    assert parsed["freq_mean"] == 1234
    assert parsed["freq_stddev"] == 56
    assert parsed["delay_mean"] == 700
    assert parsed["delay_stddev"] == 8


def test_rms_summary_negative_freq_mean(parser):
    parsed = parser._parse_ptp4l_message(
        "rms 3 max 9 freq -42 +/- 7 delay 100 +/- 2"
    )
    assert parsed["freq_mean"] == -42


def test_rms_summary_line_parsed_end_to_end(parser):
    # Full raw line through _parse_log_line: proves component routing
    # (ptp4l detection -> _parse_component_message -> _parse_ptp4l_message)
    # reaches the summary parser, not just the helper in isolation.
    summary_line = ("ptp4l[123.456]: [ptp4l.0.config] rms 5 max 12 "
                    "freq +1234 +/- 56 delay 700 +/- 8")
    entry = parser._parse_log_line(summary_line)
    assert entry.component == "ptp4l"
    assert entry.level == "info"
    assert entry.parsed_data["rms"] == 5
    assert entry.parsed_data["max_offset"] == 12
    assert entry.parsed_data["freq_mean"] == 1234
    assert entry.parsed_data["delay_stddev"] == 8


def test_summary_fields_absent_from_servo_line(parser):
    # The servo line must not accidentally populate summary fields.
    parsed = parser._parse_ptp4l_message(
        "master offset -5 s2 freq +1234 path delay 456"
    )
    assert "rms" not in parsed


# --- PR #8 servo-line fields consumed unchanged --------------------------

def test_pr8_servo_fields_consumed_unchanged(parser):
    # PR #8 delivers this parsing; assert we reuse its exact output shape.
    parsed = parser._parse_ptp4l_message(
        "master offset -5 s2 freq +1234 path delay 456"
    )
    assert parsed["offset"] == -5
    assert parsed["state"] == "s2"
    assert parsed["frequency"] == 1234
    assert parsed["path_delay"] == 456


def test_servo_state_matches_pr8_servostate_enum(parser):
    # The parsed servo state string maps onto PR #8's ServoState enum, proving
    # it is consumed rather than re-implemented here.
    from ptp_model import ServoState
    parsed = parser._parse_ptp4l_message(
        "master offset -5 s2 freq +1234 path delay 456"
    )
    assert ServoState(parsed["state"]) is ServoState.LOCKED


# --- Regression: previously-parsed fields still parse --------------------

def test_selected_clock_still_parses(parser):
    # A ptp4l BMCA selected-clock line.
    selected_clock_line = ("ptp4l[123.456]: [ptp4l.0.config] selected local "
                           "clock 001122.fffe.334455 as best master")
    entry = parser._parse_log_line(selected_clock_line)
    assert entry.component == "ptp4l"
    assert entry.parsed_data["selected_clock"] == "local"


def test_port_state_still_parses(parser):
    # A ptp4l port-state transition line.
    port_state_line = ("ptp4l[123.456]: [ptp4l.0.config] port 1: LISTENING to "
                       "MASTER on ANNOUNCE_RECEIPT_TIMEOUT_EXPIRES")
    entry = parser._parse_log_line(port_state_line)
    assert entry.component == "ptp4l"
    assert entry.parsed_data["port"] == 1
    assert entry.parsed_data["from_state"] == "LISTENING"
    assert entry.parsed_data["to_state"] == "MASTER"


def test_phc2sys_offset_still_parses(parser):
    # A phc2sys CLOCK_REALTIME offset line.
    phc2sys_line = ("phc2sys[13465352.526]: [ptp4l.0.config:6] CLOCK_REALTIME "
                    "phc offset       -12 s2 freq   -6701 delay    565")
    entry = parser._parse_log_line(phc2sys_line)
    assert entry.component == "phc2sys"
    assert entry.parsed_data["offset"] == -12
    assert entry.parsed_data["state"] == "s2"
    assert entry.parsed_data["frequency"] == -6701
    assert entry.parsed_data["delay"] == 565


def test_parse_log_line_returns_logentry_shape(parser):
    # Return conventions unchanged: LogEntry with the same attributes.
    servo_line = ("ptp4l[123.456]: [ptp4l.0.config] master offset -5 s2 "
                  "freq +1234 path delay 456")
    entry = parser._parse_log_line(servo_line)
    assert entry.component == "ptp4l"
    assert entry.level == "info"
    assert isinstance(entry.parsed_data, dict)
    assert entry.parsed_data["offset"] == -5
