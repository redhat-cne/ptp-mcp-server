import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from ptp_log_parser import LogEntry, PTPLogParser
from ptp_tools import PTPTools


def log(timestamp, component, message, parsed_data):
    return LogEntry(timestamp, component, "info", message, parsed_data)


class ParserReviewFixesTest(unittest.TestCase):
    def setUp(self):
        self.parser = PTPLogParser()
        self.now = datetime.now()

    def test_old_dpll_event_format_is_preserved(self):
        parsed = self.parser._parse_dpll_message(
            "dpll event sent for (ens8f0): state s2, Offset 1, In spec true, "
            "Source ptp4l lost false, On holdover false"
        )
        self.assertEqual(parsed["state"], "s2")
        self.assertTrue(parsed["in_spec"])

    def test_software_status_does_not_override_dpll_loss(self):
        logs = [
            log(self.now, "dpll", "", {"status": 1, "in_spec": False, "offset": 5000}),
            log(self.now + timedelta(seconds=1), "phc2sys", "", {"state": "s2", "offset": 1}),
            log(self.now + timedelta(seconds=2), "ptp4l", "", {"to_state": "SLAVE"}),
        ]
        result = self.parser.extract_sync_status(logs)
        self.assertFalse(result["dpll_locked"])
        self.assertFalse(result["offset_in_range"])

    def test_phc_offset_does_not_infer_configured_range(self):
        result = self.parser.extract_sync_status([
            log(self.now, "phc2sys", "", {"state": "s2", "offset": 1}),
        ])
        self.assertFalse(result["offset_in_range"])

    def test_high_variance_is_unstable_without_clockcheck_events(self):
        self.assertEqual(self.parser._determine_stability({"std_dev": 300}, 0), "unstable")

    def test_latest_gnss_no_fix_clears_availability(self):
        logs = [
            log(self.now + timedelta(seconds=1), "gnss", "gnss_status 0", {"gnss_status": 0}),
            log(self.now, "gnss", "gnss_status 3", {"gnss_status": 3}),
        ]
        result = self.parser.extract_gnss_status(logs)
        self.assertEqual(result["gnss_status"], 0)
        self.assertFalse(result["gnss_available"])


class ToolReviewFixesTest(unittest.IsolatedAsyncioTestCase):
    async def test_port_filter_uses_interface_name_for_all_results(self):
        tools = PTPTools()
        logs = [
            log(datetime.now(), "ptp4l", "port 1 (ens1f0): LISTENING to SLAVE", {}),
            log(datetime.now(), "ptp4l", "port 2 (ens2f0): LISTENING to MASTER", {}),
        ]
        tools.log_parser.get_ptp_logs = AsyncMock(return_value=logs)
        tools.run_pmc_query = AsyncMock(return_value={"success": False})

        result = await tools.get_port_status({"interface": "ens1f0"})

        self.assertEqual(set(result["ports"]), {"1"})
        self.assertEqual(set(result["current_states"]), {"1"})
        self.assertEqual([item["interface"] for item in result["transitions"]], ["ens1f0"])

    async def test_grandmaster_is_not_reported_as_slave(self):
        tools = PTPTools()
        tools._resolve_config_tags = Mock(return_value=None)
        tools.log_parser.get_ptp_logs = AsyncMock(return_value=[])
        tools.config_parser.get_ptp_configs = AsyncMock(return_value={})
        tools.model.create_ptp_configuration = Mock(
            return_value=SimpleNamespace(profiles=[], priorities={})
        )
        tools.model.get_clock_hierarchy = Mock(return_value={
            "current_clock": {"type": "GM", "domain": 24, "priorities": {}},
            "grandmaster": None,
            "parent_clock": None,
            "steps_removed": 0,
        })
        tools.log_parser.extract_clock_hierarchy = Mock(return_value={})
        tools.run_pmc_query = AsyncMock(return_value={"success": False})

        result = await tools.get_clock_hierarchy({"include_ports": False})

        self.assertEqual(result["hierarchy_chain"][-1]["status"], "grandmaster")
        self.assertIn("(grandmaster)", result["summary"])


if __name__ == "__main__":
    unittest.main()
