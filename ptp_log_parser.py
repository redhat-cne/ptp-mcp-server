#!/usr/bin/env python3
"""
PTP Log Parser - Parses linuxptp daemon logs and extracts structured information
"""

import json
import logging
import re
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from kube_utils import build_oc_command
from ptp_model import CLOCK_CLASS_DESCRIPTIONS

logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    component: str
    level: str
    message: str
    parsed_data: Dict[str, Any]

class PTPLogParser:
    """Parser for linuxptp daemon logs"""
    
    def __init__(self):
        self.namespace = "openshift-ptp"
        self.daemon_name = "linuxptp-daemon"
        self.container_name = "linuxptp-daemon-container"
        
        # Regex patterns for different log components
        self.patterns = {
            "timestamp": r"(\d{2}:\d{2}:\d{2}\.\d{6})",
            "ptp4l": r"ptp4l\[(\d+\.\d+)\]:\s*\[([^\]]+)\]\s*(.+)",
            "phc2sys": r"phc2sys\[(\d+\.\d+)\]:\s*\[([^\]]+)\]\s*(.+)",
            "ts2phc": r"ts2phc\[(\d+\.\d+)\]:\s*\[([^\]]+)\]\s*(.+)",
            "dpll": r"dpll\[(\d+)\]:\[([^\]]+)\]\s*(.+)",
            "gnss": r"gnss\[(\d+)\]:\[([^\]]+)\]\s*(.+)",
            "gm": r"GM\[(\d+)\]:\[([^\]]+)\]\s*(.+)",
            "go_log": r"I(\d{4})\s+(\d{2}:\d{2}:\d{2}\.\d{6})\s+(\d+)\s+([^:]+):(\d+)\]\s*(.+)"
        }

        # Extended patterns for advanced diagnostics
        self.extended_patterns = {
            "pmc_grandmaster_identity": r"grandmasterIdentity\s+([a-f0-9.]+)",
            "pmc_clock_class": r"gm\.ClockClass\s+(\d+)",
            "pmc_clock_accuracy": r"gm\.ClockAccuracy\s+(0x[0-9a-fA-F]+)",
            "pmc_priority1": r"grandmasterPriority1\s+(\d+)",
            "pmc_priority2": r"grandmasterPriority2\s+(\d+)",
            "pmc_parent_port": r"parentPortIdentity\s+([a-f0-9.-]+)",
            "clockcheck": r"clockcheck:\s*(.+)",
            "servo_state": r"offset\s+(-?\d+)\s+(s[0-2])\s+freq\s+(-?\d+)",
        }

    async def get_ptp_logs(self, namespace: str = None, lines: int = 1000, since: str = None, kubeconfig_path: str = None) -> List[LogEntry]:
        """Get PTP logs from OpenShift cluster

        Args:
            namespace: Kubernetes namespace (default: openshift-ptp)
            lines: Number of log lines to retrieve
            since: Time since to get logs (e.g., '1h', '30m')
            kubeconfig_path: Path to kubeconfig file (optional, uses default cluster if not provided)
        """
        if namespace is None:
            namespace = self.namespace

        try:
            cmd = build_oc_command(kubeconfig_path)
            cmd.extend([
                "logs", f"ds/{self.daemon_name}",
                "-c", self.container_name,
                "-n", namespace,
                "--tail", str(lines)
            ])

            if since:
                cmd.extend(["--since", since])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                raise Exception(f"Failed to get PTP logs: {result.stderr}")

            # Parse log lines
            log_lines = result.stdout.strip().split('\n')
            return [self._parse_log_line(line) for line in log_lines if line.strip()]

        except subprocess.TimeoutExpired:
            raise Exception("Timeout getting PTP logs")
        except Exception as e:
            logger.error(f"Error getting PTP logs: {str(e)}")
            raise
    
    def _parse_log_line(self, line: str) -> LogEntry:
        """Parse individual log line into structured format"""
        # Try to parse timestamp first
        timestamp_match = re.search(self.patterns["timestamp"], line)
        timestamp = None
        if timestamp_match:
            try:
                timestamp = datetime.strptime(timestamp_match.group(1), "%H:%M:%S.%f")
                # Use current date if timestamp doesn't include date
                timestamp = timestamp.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
            except ValueError:
                pass
        
        # Try different log formats
        parsed_data = {}
        component = "unknown"
        level = "info"
        message = line
        
        # Try Go-style logs first
        go_match = re.match(self.patterns["go_log"], line)
        if go_match:
            level = "info"
            timestamp_str = go_match.group(2)
            try:
                timestamp = datetime.strptime(timestamp_str, "%H:%M:%S.%f")
                timestamp = timestamp.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
            except ValueError:
                pass
            component = go_match.group(4)
            message = go_match.group(6)
            parsed_data = self._parse_go_log_message(message, component)
        else:
            # Try PTP component logs
            for comp_name, pattern in self.patterns.items():
                if comp_name in ["timestamp", "go_log"]:
                    continue
                    
                match = re.match(pattern, line)
                if match:
                    component = comp_name
                    message = match.group(3)
                    parsed_data = self._parse_component_message(message, component)
                    break
        
        return LogEntry(
            timestamp=timestamp or datetime.now(),
            component=component,
            level=level,
            message=message,
            parsed_data=parsed_data
        )
    
    def _parse_go_log_message(self, message: str, component: str) -> Dict[str, Any]:
        """Parse Go-style log messages"""
        parsed = {}
        
        # Parse DPLL messages
        if "dpll" in component.lower():
            parsed.update(self._parse_dpll_message(message))
        elif "gnss" in component.lower():
            parsed.update(self._parse_gnss_message(message))
        elif "stats" in component.lower():
            parsed.update(self._parse_stats_message(message))
        elif "event" in component.lower():
            parsed.update(self._parse_event_message(message))
        
        return parsed
    
    def _parse_dpll_message(self, message: str) -> Dict[str, Any]:
        """Parse DPLL-related messages"""
        parsed = {}
        
        # Extract offset information
        offset_match = re.search(r"offset to (-?\d+) ns", message)
        if offset_match:
            parsed["offset_ns"] = int(offset_match.group(1))
        
        # Extract clock ID
        clock_match = re.search(r"clock id (\d+)", message)
        if clock_match:
            parsed["clock_id"] = clock_match.group(1)
        
        # Extract interface
        iface_match = re.search(r"iface (\S+)", message)
        if iface_match:
            parsed["interface"] = iface_match.group(1)
        
        # Extract DPLL state
        state_match = re.search(r"state is ([^(]+)", message)
        if state_match:
            parsed["dpll_state"] = state_match.group(1)
        
        # Extract decision information
        decision_match = re.search(r"decision: Status (\d+), Offset (-?\d+), In spec (\w+), Source GNSS lost (\w+), On holdover (\w+)", message)
        if decision_match:
            parsed["status"] = int(decision_match.group(1))
            parsed["offset"] = int(decision_match.group(2))
            parsed["in_spec"] = decision_match.group(3) == "true"
            parsed["source_lost"] = decision_match.group(4) == "true"
            parsed["on_holdover"] = decision_match.group(5) == "true"
        
        return parsed
    
    def _parse_gnss_message(self, message: str) -> Dict[str, Any]:
        """Parse GNSS-related messages"""
        parsed = {}
        
        # Extract GNSS status
        status_match = re.search(r"gnss_status (\d+)", message)
        if status_match:
            parsed["gnss_status"] = int(status_match.group(1))
        
        # Extract offset
        offset_match = re.search(r"offset (\d+)", message)
        if offset_match:
            parsed["offset"] = int(offset_match.group(1))
        
        return parsed
    
    def _parse_stats_message(self, message: str) -> Dict[str, Any]:
        """Parse stats-related messages"""
        parsed = {}
        
        # Extract state update
        state_match = re.search(r"state updated for (\w+) =(\w+)", message)
        if state_match:
            parsed["component"] = state_match.group(1)
            parsed["state"] = state_match.group(2)
        
        return parsed
    
    def _parse_event_message(self, message: str) -> Dict[str, Any]:
        """Parse event-related messages"""
        parsed = {}
        
        # Extract state information
        state_match = re.search(r"dpll State (\w+), gnss State (\w+), tsphc state (\w+), gm state (\w+)", message)
        if state_match:
            parsed["dpll_state"] = state_match.group(1)
            parsed["gnss_state"] = state_match.group(2)
            parsed["ts2phc_state"] = state_match.group(3)
            parsed["gm_state"] = state_match.group(4)
        
        return parsed
    
    def _parse_component_message(self, message: str, component: str) -> Dict[str, Any]:
        """Parse PTP component messages (ptp4l, phc2sys, ts2phc)"""
        parsed = {}
        
        if component == "phc2sys":
            parsed.update(self._parse_phc2sys_message(message))
        elif component == "ts2phc":
            parsed.update(self._parse_ts2phc_message(message))
        elif component == "ptp4l":
            parsed.update(self._parse_ptp4l_message(message))
        elif component == "dpll":
            parsed.update(self._parse_dpll_component_message(message))
        elif component == "gnss":
            parsed.update(self._parse_gnss_component_message(message))
        elif component == "gm":
            parsed.update(self._parse_gm_message(message))
        
        return parsed
    
    def _parse_phc2sys_message(self, message: str) -> Dict[str, Any]:
        """Parse phc2sys messages"""
        parsed = {}
        
        # Extract offset, frequency, and delay
        match = re.search(r"CLOCK_REALTIME phc offset\s+(-?\d+)\s+(\w+)\s+freq\s+(-?\d+)\s+delay\s+(\d+)", message)
        if match:
            parsed["offset"] = int(match.group(1))
            parsed["state"] = match.group(2)
            parsed["frequency"] = int(match.group(3))
            parsed["delay"] = int(match.group(4))
        
        return parsed
    
    def _parse_ts2phc_message(self, message: str) -> Dict[str, Any]:
        """Parse ts2phc messages"""
        parsed = {}
        
        # Extract offset and frequency
        match = re.search(r"offset\s+(-?\d+)\s+(\w+)\s+freq\s+([+-]\d+)", message)
        if match:
            parsed["offset"] = int(match.group(1))
            parsed["state"] = match.group(2)
            parsed["frequency"] = int(match.group(3))
        
        # Extract NMEA information
        nmea_match = re.search(r"nmea delay: (\d+) ns", message)
        if nmea_match:
            parsed["nmea_delay_ns"] = int(nmea_match.group(1))
        
        # Extract NMEA sentences
        nmea_sentence_match = re.search(r"nmea sentence: ([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+)", message)
        if nmea_sentence_match:
            parsed["nmea_type"] = nmea_sentence_match.group(1)
            parsed["nmea_time"] = nmea_sentence_match.group(2)
            parsed["nmea_lat"] = nmea_sentence_match.group(3)
            parsed["nmea_lat_dir"] = nmea_sentence_match.group(4)
            parsed["nmea_lon"] = nmea_sentence_match.group(5)
            parsed["nmea_lon_dir"] = nmea_sentence_match.group(6)
        
        return parsed
    
    def _parse_ptp4l_message(self, message: str) -> Dict[str, Any]:
        """Parse ptp4l messages"""
        parsed = {}
        
        # Extract BMCA information
        bmca_match = re.search(r"selected (\w+) clock", message)
        if bmca_match:
            parsed["selected_clock"] = bmca_match.group(1)
        
        # Extract port state
        port_match = re.search(r"port (\d+): ([\w\s]+)", message)
        if port_match:
            parsed["port"] = int(port_match.group(1))
            parsed["port_state"] = port_match.group(2).strip()
        
        return parsed
    
    def _parse_dpll_component_message(self, message: str) -> Dict[str, Any]:
        """Parse DPLL component messages"""
        parsed = {}
        
        # Extract frequency status, offset, phase status, PPS status
        match = re.search(r"(\w+) frequency_status (\d+) offset (-?\d+) phase_status (\d+) pps_status (\d+) (\w+)", message)
        if match:
            parsed["interface"] = match.group(1)
            parsed["frequency_status"] = int(match.group(2))
            parsed["offset"] = int(match.group(3))
            parsed["phase_status"] = int(match.group(4))
            parsed["pps_status"] = int(match.group(5))
            parsed["state"] = match.group(6)
        
        return parsed
    
    def _parse_gnss_component_message(self, message: str) -> Dict[str, Any]:
        """Parse GNSS component messages"""
        parsed = {}
        
        # Extract GNSS status and offset
        match = re.search(r"(\w+) gnss_status (\d+) offset (\d+) (\w+)", message)
        if match:
            parsed["interface"] = match.group(1)
            parsed["gnss_status"] = int(match.group(2))
            parsed["offset"] = int(match.group(3))
            parsed["state"] = match.group(4)
        
        return parsed
    
    def _parse_gm_message(self, message: str) -> Dict[str, Any]:
        """Parse GM (Grandmaster) messages"""
        parsed = {}
        
        # Extract GM status
        match = re.search(r"(\w+) T-GM-STATUS (\w+)", message)
        if match:
            parsed["interface"] = match.group(1)
            parsed["gm_status"] = match.group(2)
        
        return parsed
    
    def search_logs(self, logs: List[LogEntry], query: str, time_range: str = None, log_level: str = None) -> List[LogEntry]:
        """Search logs for specific patterns"""
        filtered_logs = logs
        
        # Apply time range filter
        if time_range:
            cutoff_time = self._get_cutoff_time(time_range)
            filtered_logs = [log for log in filtered_logs if log.timestamp >= cutoff_time]
        
        # Apply log level filter
        if log_level:
            filtered_logs = [log for log in filtered_logs if log.level == log_level]
        
        # Apply query filter
        if query:
            query_lower = query.lower()
            filtered_logs = [
                log for log in filtered_logs 
                if query_lower in log.message.lower() or 
                   any(query_lower in str(v).lower() for v in log.parsed_data.values())
            ]
        
        return filtered_logs
    
    def _get_cutoff_time(self, time_range: str) -> datetime:
        """Get cutoff time based on time range string"""
        now = datetime.now()
        
        if time_range == "last_hour":
            return now - timedelta(hours=1)
        elif time_range == "last_day":
            return now - timedelta(days=1)
        elif time_range == "last_week":
            return now - timedelta(weeks=1)
        elif time_range.startswith("last_"):
            # Parse custom time ranges like "last_30m", "last_2h"
            import re
            match = re.match(r"last_(\d+)([mhd])", time_range)
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                if unit == "m":
                    return now - timedelta(minutes=amount)
                elif unit == "h":
                    return now - timedelta(hours=amount)
                elif unit == "d":
                    return now - timedelta(days=amount)
        
        # Default to last hour
        return now - timedelta(hours=1)
    
    def extract_grandmaster_info(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Extract grandmaster information from logs"""
        gm_info = {
            "status": "unknown",
            "interface": None,
            "last_seen": None,
            "offset": None,
            "frequency": None
        }
        
        # Look for GM status messages
        gm_logs = [log for log in logs if log.component == "gm"]
        if gm_logs:
            latest_gm = max(gm_logs, key=lambda x: x.timestamp)
            gm_info["status"] = latest_gm.parsed_data.get("gm_status", "unknown")
            gm_info["interface"] = latest_gm.parsed_data.get("interface")
            gm_info["last_seen"] = latest_gm.timestamp
        
        # Look for phc2sys offset information
        phc2sys_logs = [log for log in logs if log.component == "phc2sys"]
        if phc2sys_logs:
            latest_phc2sys = max(phc2sys_logs, key=lambda x: x.timestamp)
            gm_info["offset"] = latest_phc2sys.parsed_data.get("offset")
            gm_info["frequency"] = latest_phc2sys.parsed_data.get("frequency")
        
        return gm_info
    
    def extract_sync_status(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Extract synchronization status from logs"""
        sync_status = {
            "dpll_locked": False,
            "gnss_available": False,
            "offset_in_range": False,
            "last_offset": None,
            "last_update": None
        }
        
        # Look for DPLL decision messages
        dpll_logs = [log for log in logs if "dpll" in log.component.lower() and "decision" in log.message]
        if dpll_logs:
            latest_dpll = max(dpll_logs, key=lambda x: x.timestamp)
            parsed = latest_dpll.parsed_data
            sync_status["dpll_locked"] = parsed.get("status", 0) == 3
            sync_status["offset_in_range"] = parsed.get("in_spec", False)
            sync_status["last_offset"] = parsed.get("offset")
            sync_status["last_update"] = latest_dpll.timestamp
        
        # Look for GNSS status
        gnss_logs = [log for log in logs if "gnss" in log.component.lower()]
        if gnss_logs:
            latest_gnss = max(gnss_logs, key=lambda x: x.timestamp)
            sync_status["gnss_available"] = latest_gnss.parsed_data.get("gnss_status", 0) > 0
        
        return sync_status
    
    def extract_clock_hierarchy(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Extract clock hierarchy information from logs"""
        hierarchy = {
            "grandmaster": None,
            "boundary_clocks": [],
            "ordinary_clocks": [],
            "transparent_clocks": []
        }
        
        # Look for ptp4l BMCA messages
        ptp4l_logs = [log for log in logs if log.component == "ptp4l" and "selected" in log.message]
        for log in ptp4l_logs:
            if "grandmaster" in log.parsed_data.get("selected_clock", "").lower():
                hierarchy["grandmaster"] = {
                    "status": "active",
                    "last_seen": log.timestamp
                }
        
        return hierarchy

    def _compute_offset_stats(self, offsets: List[int]) -> Dict[str, Any]:
        """Compute offset statistics from a list of offset values"""
        stats = {"mean": None, "std_dev": None, "max": None, "min": None, "count": 0}
        if not offsets:
            return stats
        stats["count"] = len(offsets)
        stats["mean"] = sum(offsets) / len(offsets)
        stats["max"] = max(offsets)
        stats["min"] = min(offsets)
        if len(offsets) > 1:
            mean = stats["mean"]
            variance = sum((x - mean) ** 2 for x in offsets) / len(offsets)
            stats["std_dev"] = variance ** 0.5
        return stats

    def _compute_frequency_stats(self, frequencies: List[int]) -> Dict[str, Any]:
        """Compute frequency statistics from a list of frequency values"""
        stats = {"mean": None, "current": None, "trend": "unknown"}
        if not frequencies:
            return stats
        stats["mean"] = sum(frequencies) / len(frequencies)
        stats["current"] = frequencies[-1]
        if len(frequencies) >= 10:
            half = len(frequencies) // 2
            first_half_avg = sum(frequencies[:half]) / half
            second_half_avg = sum(frequencies[half:]) / (len(frequencies) - half)
            diff = second_half_avg - first_half_avg
            if abs(diff) < 100:
                stats["trend"] = "stable"
            elif diff > 0:
                stats["trend"] = "increasing"
            else:
                stats["trend"] = "decreasing"
        return stats

    def _determine_stability(self, offset_stats: Dict[str, Any], clockcheck_count: int) -> str:
        """Determine stability rating from offset stats and clockcheck event count"""
        if offset_stats["std_dev"] is None:
            return "unknown"
        if offset_stats["std_dev"] < 50 and clockcheck_count == 0:
            return "stable"
        elif offset_stats["std_dev"] < 200 or clockcheck_count <= 2:
            return "degraded"
        return "unstable"

    def extract_servo_statistics(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Extract servo performance statistics from ptp4l and phc2sys logs"""
        component_data = {}
        clockcheck_events = []

        for log in logs:
            if log.component not in ("ptp4l", "phc2sys"):
                continue

            data = component_data.setdefault(log.component, {
                "offsets": [], "frequencies": [], "servo_states": []
            })
            if "offset" in log.parsed_data:
                data["offsets"].append(log.parsed_data["offset"])
            if "frequency" in log.parsed_data:
                data["frequencies"].append(log.parsed_data["frequency"])
            if "state" in log.parsed_data:
                data["servo_states"].append(log.parsed_data["state"])

            # Check for clockcheck events from any component
            if "clockcheck" in log.message.lower():
                match = re.search(self.extended_patterns["clockcheck"], log.message)
                if match:
                    clockcheck_events.append({
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                        "component": log.component,
                        "message": match.group(1),
                        "offset_at_event": log.parsed_data.get("offset")
                    })

        # Build per-component stats with ptp4l listed first
        components = {}
        for comp in ("ptp4l", "phc2sys"):
            data = component_data.get(comp)
            if data is None:
                continue
            offset_stats = self._compute_offset_stats(data["offsets"])
            components[comp] = {
                "servo_state": data["servo_states"][-1] if data["servo_states"] else "unknown",
                "offset_stats": offset_stats,
                "frequency_stats": self._compute_frequency_stats(data["frequencies"]),
                "stability": self._determine_stability(offset_stats, len(clockcheck_events)),
            }

        # Overall servo state: prefer ptp4l, fall back to phc2sys
        overall_servo_state = "unknown"
        for comp in ("ptp4l", "phc2sys"):
            if comp in components and components[comp]["servo_state"] != "unknown":
                overall_servo_state = components[comp]["servo_state"]
                break

        # Overall stability: use ptp4l if available, else phc2sys
        overall_stability = "unknown"
        for comp in ("ptp4l", "phc2sys"):
            if comp in components:
                overall_stability = components[comp]["stability"]
                break

        stats = {
            "servo_state": overall_servo_state,
            "clockcheck_events": clockcheck_events,
            "stability": overall_stability,
            "components": components,
        }

        # Preserve top-level offset_stats/frequency_stats from ptp4l (preferred) or phc2sys
        primary = components.get("ptp4l", components.get("phc2sys"))
        if primary:
            stats["offset_stats"] = primary["offset_stats"]
            stats["frequency_stats"] = primary["frequency_stats"]
        else:
            stats["offset_stats"] = {"mean": None, "std_dev": None, "max": None, "min": None, "count": 0}
            stats["frequency_stats"] = {"mean": None, "current": None, "trend": "unknown"}

        return stats

    def _get_clock_class_description(self, clock_class: int) -> str:
        """Get human-readable description of clock class per ITU-T G.8275.1"""
        return CLOCK_CLASS_DESCRIPTIONS.get(clock_class, f"Clock class {clock_class}")

    def parse_pmc_output(self, pmc_output: str) -> Dict[str, Any]:
        """Parse PMC command output into structured data"""
        result = {"data": {}}

        match = re.search(self.extended_patterns["pmc_grandmaster_identity"], pmc_output)
        if match:
            result["grandmaster_identity"] = match.group(1)
            result["data"]["grandmaster_identity"] = match.group(1)

        match = re.search(self.extended_patterns["pmc_clock_class"], pmc_output)
        if match:
            result["grandmaster_clock_class"] = int(match.group(1))
            result["data"]["grandmaster_clock_class"] = int(match.group(1))

        match = re.search(self.extended_patterns["pmc_clock_accuracy"], pmc_output)
        if match:
            result["grandmaster_clock_accuracy"] = match.group(1)
            result["data"]["grandmaster_clock_accuracy"] = match.group(1)

        match = re.search(self.extended_patterns["pmc_priority1"], pmc_output)
        if match:
            result["grandmaster_priority1"] = int(match.group(1))
            result["data"]["grandmaster_priority1"] = int(match.group(1))

        match = re.search(self.extended_patterns["pmc_priority2"], pmc_output)
        if match:
            result["grandmaster_priority2"] = int(match.group(1))
            result["data"]["grandmaster_priority2"] = int(match.group(1))

        match = re.search(self.extended_patterns["pmc_parent_port"], pmc_output)
        if match:
            result["parent_port_identity"] = match.group(1)
            result["data"]["parent_port_identity"] = match.group(1)

        match = re.search(r"stepsRemoved\s+(\d+)", pmc_output)
        if match:
            result["steps_removed"] = int(match.group(1))
            result["data"]["steps_removed"] = int(match.group(1))

        match = re.search(r"offsetFromMaster\s+(-?[\d.]+)", pmc_output)
        if match:
            result["offset_from_master"] = float(match.group(1))
            result["data"]["offset_from_master"] = float(match.group(1))

        match = re.search(r"meanPathDelay\s+(-?[\d.]+)", pmc_output)
        if match:
            result["mean_path_delay"] = float(match.group(1))
            result["data"]["mean_path_delay"] = float(match.group(1))

        match = re.search(r"portIdentity\s+([a-f0-9.-]+)", pmc_output)
        if match:
            result["port_identity"] = match.group(1)
            result["data"]["port_identity"] = match.group(1)

        match = re.search(r"portState\s+(\w+)", pmc_output)
        if match:
            result["port_state"] = match.group(1)
            result["data"]["port_state"] = match.group(1)

        match = re.search(r"logMinDelayReqInterval\s+(-?\d+)", pmc_output)
        if match:
            result["log_min_delay_req_interval"] = int(match.group(1))
            result["data"]["log_min_delay_req_interval"] = int(match.group(1))

        match = re.search(r"logSyncInterval\s+(-?\d+)", pmc_output)
        if match:
            result["log_sync_interval"] = int(match.group(1))
            result["data"]["log_sync_interval"] = int(match.group(1))

        match = re.search(r"logAnnounceInterval\s+(-?\d+)", pmc_output)
        if match:
            result["log_announce_interval"] = int(match.group(1))
            result["data"]["log_announce_interval"] = int(match.group(1))

        match = re.search(r"delayMechanism\s+(\d+)", pmc_output)
        if match:
            delay_mech = int(match.group(1))
            result["delay_mechanism"] = delay_mech
            result["data"]["delay_mechanism"] = "E2E" if delay_mech == 1 else "P2P" if delay_mech == 2 else str(delay_mech)

        return result 