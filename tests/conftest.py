"""Shared fixtures for cluster-free log-parser tests.

Only the parser object is shared here. The raw linuxptp log lines under test
are written inline in each test (rather than as fixtures in this file) so the
exact string being parsed is visible alongside the assertions that check it.
Tests call PTPLogParser methods directly on those strings, so no live cluster
or `oc` binary is required.
"""

import pytest

from ptp_log_parser import PTPLogParser


@pytest.fixture
def parser():
    """A fresh PTPLogParser instance (no cluster access performed)."""
    return PTPLogParser()
