"""Shared fixtures for cluster-free log-parser tests.

Every fixture is a representative *raw* linuxptp log line (as would be emitted
by the linuxptp-daemon container). Tests call PTPLogParser methods directly on
these strings, so no live cluster or `oc` binary is required.
"""

import pytest

from ptp_log_parser import PTPLogParser


@pytest.fixture
def parser():
    """A fresh PTPLogParser instance (no cluster access performed)."""
    return PTPLogParser()


@pytest.fixture
def servo_line():
    """Normal ptp4l servo line (locked, s2) — the healthy steady-state case."""
    return "ptp4l[123.456]: [ptp4l.0.config] master offset -5 s2 freq +1234 path delay 456"


@pytest.fixture
def summary_line():
    """ptp4l rms/max summary statistics line."""
    return "ptp4l[123.456]: [ptp4l.0.config] rms 5 max 12 freq +1234 +/- 56 delay 700 +/- 8"


@pytest.fixture
def clockcheck_line():
    """A clockcheck warning line."""
    return "ptp4l[123.456]: [ptp4l.0.config] clockcheck: clock jumped backwards"


@pytest.fixture
def fault_line():
    """A ptp4l fault (error) line."""
    return "ptp4l[123.456]: [ptp4l.0.config] port 1: fault detected on interface"


@pytest.fixture
def timeout_line():
    """An announce/connection timeout (error) line."""
    return "ptp4l[123.456]: [ptp4l.0.config] timed out while polling for tx timestamp"


@pytest.fixture
def healthy_dpll_decision_line():
    """A routine, healthy DPLL decision line — in spec, not on holdover.

    Contains the substring "holdover" ("On holdover false"), so it guards
    against a bare-substring severity marker mis-classifying it as warning.
    """
    return ("dpll[123]:[ptp4l.0.config] decision: Status 3, Offset 5, "
            "In spec true, Source GNSS lost false, On holdover false")


@pytest.fixture
def out_of_spec_dpll_decision_line():
    """A DPLL decision line reporting an out-of-spec ("In spec false") clock."""
    return ("dpll[123]:[ptp4l.0.config] decision: Status 3, Offset 9999, "
            "In spec false, Source GNSS lost false, On holdover true")


@pytest.fixture
def phc2sys_line():
    """A phc2sys CLOCK_REALTIME offset line."""
    return "phc2sys[13465352.526]: [ptp4l.0.config:6] CLOCK_REALTIME phc offset       -12 s2 freq   -6701 delay    565"


@pytest.fixture
def selected_clock_line():
    """A ptp4l BMCA selected-clock line."""
    return "ptp4l[123.456]: [ptp4l.0.config] selected local clock 001122.fffe.334455 as best master"


@pytest.fixture
def port_state_line():
    """A ptp4l port-state transition line."""
    return "ptp4l[123.456]: [ptp4l.0.config] port 1: LISTENING to MASTER on ANNOUNCE_RECEIPT_TIMEOUT_EXPIRES"
