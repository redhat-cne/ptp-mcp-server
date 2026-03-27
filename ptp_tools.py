#!/usr/bin/env python3
"""
PTP Tools - Implementation of MCP tools for PTP monitoring
"""

import json
import logging
import re
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ptp_config_parser import PTPConfigParser
from ptp_log_parser import PTPLogParser
from ptp_model import PTPModel
from ptp_query_engine import PTPQueryEngine
from kube_utils import kubeconfig_from_base64, build_oc_command

logger = logging.getLogger(__name__)

class PTPTools:
    """Implementation of PTP MCP tools"""

    def __init__(self):
        self.config_parser = PTPConfigParser()
        self.log_parser = PTPLogParser()
        self.model = PTPModel()
        self.query_engine = PTPQueryEngine()

    async def get_ptp_config(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PTP configuration from OpenShift cluster"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get raw configuration
                config_data = await self.config_parser.get_ptp_configs(namespace, kubeconfig_path=kubeconfig_path)

                # Create structured configuration
                ptp_config = self.model.create_ptp_configuration(config_data)

                # Validate configuration
                validation = self.config_parser.validate_config(config_data["items"][0])

                # Validate ITU-T compliance
                itu_validation = self.model.validate_itu_t_compliance(ptp_config)

                return {
                    "success": True,
                    "configuration": {
                        "name": ptp_config.name,
                        "namespace": ptp_config.namespace,
                        "clock_type": ptp_config.clock_type.value,
                        "domain": ptp_config.domain,
                        "priorities": ptp_config.priorities,
                        "clock_class": ptp_config.clock_class,
                        "sync_intervals": ptp_config.sync_intervals,
                        "thresholds": ptp_config.thresholds,
                        "profiles": ptp_config.profiles,
                        "recommendations": ptp_config.recommendations
                    },
                    "validation": validation,
                    "itu_compliance": itu_validation,
                    "raw_data": config_data
                }

        except Exception as e:
            logger.error(f"Error getting PTP config: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "configuration": None
            }

    async def get_ptp_logs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PTP logs from OpenShift cluster"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            lines = arguments.get("lines", 1000)
            since = arguments.get("since")
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get logs
                logs = await self.log_parser.get_ptp_logs(namespace, lines, since, kubeconfig_path=kubeconfig_path)

                # Extract structured information
                gm_info = self.log_parser.extract_grandmaster_info(logs)
                sync_status = self.log_parser.extract_sync_status(logs)
                clock_hierarchy = self.log_parser.extract_clock_hierarchy(logs)

                return {
                    "success": True,
                    "logs_count": len(logs),
                    "grandmaster": gm_info,
                    "sync_status": sync_status,
                    "clock_hierarchy": clock_hierarchy,
                    "log_entries": [
                        {
                            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                            "component": log.component,
                            "level": log.level,
                            "message": log.message,
                            "parsed_data": log.parsed_data
                        }
                        for log in logs[-100:]  # Return last 100 entries for brevity
                    ]
                }

        except Exception as e:
            logger.error(f"Error getting PTP logs: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "logs_count": 0
            }

    async def search_logs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PTP logs for specific patterns"""
        try:
            query = arguments.get("query", "")
            time_range = arguments.get("time_range")
            log_level = arguments.get("log_level")
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get logs first
                logs = await self.log_parser.get_ptp_logs(kubeconfig_path=kubeconfig_path)

                # Search logs
                filtered_logs = self.log_parser.search_logs(logs, query, time_range, log_level)

                return {
                    "success": True,
                    "query": query,
                    "time_range": time_range,
                    "log_level": log_level,
                    "total_logs": len(logs),
                    "matching_logs": len(filtered_logs),
                    "results": [
                        {
                            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                            "component": log.component,
                            "level": log.level,
                            "message": log.message,
                            "parsed_data": log.parsed_data
                        }
                        for log in filtered_logs
                    ]
                }

        except Exception as e:
            logger.error(f"Error searching logs: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def get_grandmaster_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get current grandmaster status"""
        try:
            detailed = arguments.get("detailed", False)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get logs to extract grandmaster info
                logs = await self.log_parser.get_ptp_logs(kubeconfig_path=kubeconfig_path)
                gm_info = self.log_parser.extract_grandmaster_info(logs)

                # Get configuration for additional context
                config_data = await self.config_parser.get_ptp_configs(kubeconfig_path=kubeconfig_path)
                ptp_config = self.model.create_ptp_configuration(config_data)

                result = {
                    "success": True,
                    "grandmaster": gm_info,
                    "configuration_context": {
                        "domain": ptp_config.domain,
                        "clock_type": ptp_config.clock_type.value,
                        "clock_class": ptp_config.clock_class
                    }
                }

                if detailed:
                    # Add more detailed analysis
                    sync_status = self.log_parser.extract_sync_status(logs)
                    result["sync_status"] = sync_status

                    # Analyze BMCA state
                    bmca_role = self.model.analyze_bmca_state(ptp_config, logs)
                    result["bmca_role"] = bmca_role.value

                return result

        except Exception as e:
            logger.error(f"Error getting grandmaster status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "grandmaster": {"status": "unknown"}
            }

    async def analyze_sync_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze PTP synchronization status"""
        try:
            include_offsets = arguments.get("include_offsets", True)
            include_bmca = arguments.get("include_bmca", True)
            include_path_delay = arguments.get("include_path_delay", False)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get logs and configuration
                logs = await self.log_parser.get_ptp_logs(kubeconfig_path=kubeconfig_path)
                config_data = await self.config_parser.get_ptp_configs(kubeconfig_path=kubeconfig_path)
                ptp_config = self.model.create_ptp_configuration(config_data)

                # Extract sync status
                sync_status = self.log_parser.extract_sync_status(logs)

                # Analyze sync status using model
                model_sync_status = self.model.analyze_sync_status(ptp_config, logs)

                result = {
                    "success": True,
                    "sync_status": sync_status,
                    "model_sync_status": model_sync_status.value,
                    "configuration": {
                        "clock_type": ptp_config.clock_type.value,
                        "domain": ptp_config.domain,
                        "clock_class": ptp_config.clock_class
                    }
                }

                if include_offsets:
                    # Get offset trend
                    offset_trend = self.model.get_offset_trend(logs)
                    result["offset_trend"] = offset_trend

                if include_bmca:
                    # Analyze BMCA state
                    bmca_role = self.model.analyze_bmca_state(ptp_config, logs)
                    result["bmca_role"] = bmca_role.value

                if include_path_delay:
                    # Analyze network path delay characteristics
                    result["path_delay"] = self._analyze_path_delay(logs)

                return result

        except Exception as e:
            logger.error(f"Error analyzing sync status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sync_status": {"dpll_locked": False, "offset_in_range": False}
            }

    def _analyze_path_delay(self, logs) -> Dict[str, Any]:
        """Analyze network path delay characteristics from logs"""
        delays = []
        for log in logs:
            if log.component == "phc2sys" and "delay" in log.parsed_data:
                delays.append(log.parsed_data["delay"])

        result = {
            "mean_path_delay_ns": None,
            "path_delay_variance": None,
            "min_delay_ns": None,
            "max_delay_ns": None,
            "asymmetry_detected": False,
            "delay_trend": "unknown",
            "sample_count": len(delays)
        }

        if delays:
            result["mean_path_delay_ns"] = sum(delays) / len(delays)
            result["min_delay_ns"] = min(delays)
            result["max_delay_ns"] = max(delays)

            if len(delays) > 1:
                mean = result["mean_path_delay_ns"]
                variance = sum((d - mean) ** 2 for d in delays) / len(delays)
                result["path_delay_variance"] = variance

                # Check for asymmetry (large variance suggests asymmetry issues)
                if variance > 10000:  # >100ns std dev
                    result["asymmetry_detected"] = True

                # Determine trend
                if len(delays) >= 10:
                    first_half = sum(delays[:len(delays)//2]) / (len(delays)//2)
                    second_half = sum(delays[len(delays)//2:]) / (len(delays) - len(delays)//2)
                    diff = second_half - first_half
                    if abs(diff) < 10:
                        result["delay_trend"] = "stable"
                    elif diff > 0:
                        result["delay_trend"] = "increasing"
                    else:
                        result["delay_trend"] = "decreasing"

        return result

    async def get_clock_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get current clock hierarchy"""
        try:
            include_ports = arguments.get("include_ports", True)
            include_priorities = arguments.get("include_priorities", True)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get logs and configuration
                logs = await self.log_parser.get_ptp_logs(kubeconfig_path=kubeconfig_path)
                config_data = await self.config_parser.get_ptp_configs(kubeconfig_path=kubeconfig_path)
                ptp_config = self.model.create_ptp_configuration(config_data)

                # Get clock hierarchy from model
                hierarchy = self.model.get_clock_hierarchy(ptp_config, logs)

                # Add log-based hierarchy info (grandmaster, parent clock, etc.)
                log_hierarchy = self.log_parser.extract_clock_hierarchy(logs)
                hierarchy.update(log_hierarchy)

                # Try to get steps_removed from PMC CURRENT_DATA_SET query
                try:
                    pmc_result = await self.run_pmc_query({"command": "CURRENT_DATA_SET", "kubeconfig": kubeconfig})
                    if pmc_result.get("success") and pmc_result.get("data"):
                        steps = pmc_result["data"].get("steps_removed")
                        if steps is not None:
                            hierarchy["steps_removed"] = steps
                except Exception as pmc_error:
                    logger.debug(f"Could not get steps_removed from PMC: {pmc_error}")

                # Build a clear hierarchy chain for display
                hierarchy_chain = []

                # 1. Grandmaster (top of hierarchy)
                if hierarchy.get("grandmaster"):
                    gm = hierarchy["grandmaster"]
                    hierarchy_chain.append({
                        "level": 1,
                        "role": "Grandmaster",
                        "identity": gm.get("identity"),
                        "clock_class": gm.get("clock_class"),
                        "clock_class_description": gm.get("clock_class_description"),
                        "priority1": gm.get("priority1"),
                        "priority2": gm.get("priority2"),
                        "status": gm.get("status", "active")
                    })

                # 2. Parent/Boundary Clock (intermediate - if different from GM)
                if hierarchy.get("parent_clock"):
                    parent = hierarchy["parent_clock"]
                    gm_id = (hierarchy.get("grandmaster") or {}).get("identity", "")
                    # Only add if parent is different from grandmaster
                    if parent.get("identity") and parent.get("identity") != gm_id:
                        hierarchy_chain.append({
                            "level": 2,
                            "role": "Parent Clock (Boundary Clock)",
                            "identity": parent.get("identity"),
                            "port_identity": parent.get("port_identity"),
                            "description": parent.get("description"),
                            "status": "active"
                        })

                # 3. Current node (this OpenShift node)
                hierarchy_chain.append({
                    "level": 3,
                    "role": "Current Node (Ordinary Clock)",
                    "clock_type": hierarchy.get("current_clock", {}).get("type", "OC"),
                    "domain": hierarchy.get("current_clock", {}).get("domain"),
                    "clock_class": hierarchy.get("current_clock", {}).get("clock_class"),
                    "priority1": hierarchy.get("current_clock", {}).get("priorities", {}).get("priority1"),
                    "priority2": hierarchy.get("current_clock", {}).get("priorities", {}).get("priority2"),
                    "status": "slave"
                })

                result = {
                    "success": True,
                    "hierarchy_chain": hierarchy_chain,
                    "grandmaster": hierarchy.get("grandmaster"),
                    "parent_clock": hierarchy.get("parent_clock"),
                    "current_clock": hierarchy.get("current_clock"),
                    "steps_removed": hierarchy.get("steps_removed"),
                    "summary": self._build_hierarchy_summary(hierarchy_chain, hierarchy.get("steps_removed")),
                    "visibility_note": hierarchy.get("visibility_note")
                }

                if include_ports:
                    # Add port information from configuration
                    ports = []
                    for profile in ptp_config.profiles:
                        ptp4l_conf = profile.get("ptp4lConf", {})
                        interfaces = ptp4l_conf.get("interfaces", {})
                        for interface_name, interface_config in interfaces.items():
                            ports.append({
                                "name": interface_name,
                                "master_only": interface_config.get("masterOnly", False),
                                "config": interface_config
                            })
                    result["ports"] = ports

                if include_priorities:
                    result["priorities"] = ptp_config.priorities

                return result

        except Exception as e:
            logger.error(f"Error getting clock hierarchy: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "hierarchy": {}
            }

    def _build_hierarchy_summary(self, hierarchy_chain: list, steps_removed: int = None) -> str:
        """Build a human-readable summary of the clock hierarchy"""
        if not hierarchy_chain:
            return "No clock hierarchy information available"

        lines = ["PTP Clock Hierarchy:"]

        for i, clock in enumerate(hierarchy_chain):
            indent = "  " * (clock.get("level", 1) - 1)
            arrow = "→ " if i > 0 else ""

            if clock["role"] == "Grandmaster":
                desc = clock.get("clock_class_description", "")
                lines.append(f"{indent}{arrow}Grandmaster: {clock.get('identity')} (class {clock.get('clock_class')}: {desc})")
            elif "Parent" in clock["role"]:
                lines.append(f"{indent}{arrow}Parent BC: {clock.get('identity')} (port {clock.get('port_identity')})")
            else:
                lines.append(f"{indent}{arrow}This Node: {clock.get('clock_type')} on domain {clock.get('domain')} (slave)")

        if steps_removed is not None:
            lines.append(f"\nSteps removed from grandmaster: {steps_removed}")

        return "\n".join(lines)

    async def check_ptp_health(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive PTP health check"""
        try:
            check_config = arguments.get("check_config", True)
            check_sync = arguments.get("check_sync", True)
            check_logs = arguments.get("check_logs", True)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                health_result = {
                    "success": True,
                    "overall_status": "unknown",
                    "checks": {}
                }

                # Check configuration
                if check_config:
                    try:
                        config_data = await self.config_parser.get_ptp_configs(kubeconfig_path=kubeconfig_path)
                        ptp_config = self.model.create_ptp_configuration(config_data)
                        config_validation = self.config_parser.validate_config(config_data["items"][0])
                        itu_validation = self.model.validate_itu_t_compliance(ptp_config)

                        health_result["checks"]["configuration"] = {
                            "valid": config_validation["valid"],
                            "errors": config_validation["errors"],
                            "warnings": config_validation["warnings"],
                            "itu_compliant": itu_validation["compliant"]
                        }
                    except Exception as e:
                        health_result["checks"]["configuration"] = {
                            "valid": False,
                            "error": str(e)
                        }

                # Check synchronization
                if check_sync:
                    try:
                        logs = await self.log_parser.get_ptp_logs(kubeconfig_path=kubeconfig_path)
                        sync_status = self.log_parser.extract_sync_status(logs)

                        health_result["checks"]["synchronization"] = {
                            "dpll_locked": sync_status.get("dpll_locked", False),
                            "offset_in_range": sync_status.get("offset_in_range", False),
                            "gnss_available": sync_status.get("gnss_available", False),
                            "last_offset": sync_status.get("last_offset")
                        }
                    except Exception as e:
                        health_result["checks"]["synchronization"] = {
                            "error": str(e)
                        }

                # Check logs
                if check_logs:
                    try:
                        logs = await self.log_parser.get_ptp_logs(kubeconfig_path=kubeconfig_path)

                        # Look for error and warning messages
                        error_logs = [log for log in logs if log.level == "error"]
                        warning_logs = [log for log in logs if log.level == "warning"]

                        health_result["checks"]["logs"] = {
                            "total_logs": len(logs),
                            "error_count": len(error_logs),
                            "warning_count": len(warning_logs),
                            "recent_errors": [
                                {
                                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                                    "component": log.component,
                                    "message": log.message
                                }
                                for log in error_logs[-10:]  # Last 10 errors
                            ]
                        }
                    except Exception as e:
                        health_result["checks"]["logs"] = {
                            "error": str(e)
                        }

                # Determine overall status
                config_healthy = health_result["checks"].get("configuration", {}).get("valid", False)
                sync_healthy = health_result["checks"].get("synchronization", {}).get("dpll_locked", False)
                logs_healthy = health_result["checks"].get("logs", {}).get("error_count", 0) == 0

                if config_healthy and sync_healthy and logs_healthy:
                    health_result["overall_status"] = "healthy"
                elif not config_healthy:
                    health_result["overall_status"] = "critical"
                elif not sync_healthy:
                    health_result["overall_status"] = "warning"
                else:
                    health_result["overall_status"] = "warning"

                return health_result

        except Exception as e:
            logger.error(f"Error checking PTP health: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "overall_status": "unknown"
            }

    async def query_ptp(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Natural language query interface for PTP information"""
        try:
            question = arguments.get("question", "")
            context = arguments.get("context")
            kubeconfig = arguments.get("kubeconfig")

            if not question:
                return {
                    "success": False,
                    "error": "No question provided",
                    "suggestions": self.query_engine.suggest_queries()
                }

            # Parse the query
            query_info = self.query_engine.parse_query(question, context)

            # Gather data based on query type
            data = {}

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                if query_info["query_type"] in ["grandmaster", "configuration", "sync_status", "clock_hierarchy", "health_check"]:
                    # Get configuration data
                    try:
                        config_data = await self.config_parser.get_ptp_configs(kubeconfig_path=kubeconfig_path)
                        ptp_config = self.model.create_ptp_configuration(config_data)
                        data["configuration"] = {
                            "name": ptp_config.name,
                            "clock_type": ptp_config.clock_type.value,
                            "domain": ptp_config.domain,
                            "priorities": ptp_config.priorities,
                            "clock_class": ptp_config.clock_class,
                            "sync_intervals": ptp_config.sync_intervals
                        }
                    except Exception as e:
                        data["configuration"] = {"error": str(e)}

                if query_info["query_type"] in ["grandmaster", "sync_status", "clock_hierarchy", "offset_trend", "bmca_state"]:
                    # Get log data
                    try:
                        logs = await self.log_parser.get_ptp_logs(kubeconfig_path=kubeconfig_path)
                        data["grandmaster"] = self.log_parser.extract_grandmaster_info(logs)
                        data["sync_status"] = self.log_parser.extract_sync_status(logs)
                        data["clock_hierarchy"] = self.log_parser.extract_clock_hierarchy(logs)
                        data["offset_trend"] = self.model.get_offset_trend(logs, query_info.get("time_range"))
                    except Exception as e:
                        data["logs"] = {"error": str(e)}

                if query_info["query_type"] == "itu_compliance":
                    # Get configuration for ITU compliance check
                    try:
                        config_data = await self.config_parser.get_ptp_configs(kubeconfig_path=kubeconfig_path)
                        ptp_config = self.model.create_ptp_configuration(config_data)
                        data["itu_compliance"] = self.model.validate_itu_t_compliance(ptp_config)
                    except Exception as e:
                        data["itu_compliance"] = {"error": str(e)}

                if query_info["query_type"] == "health_check":
                    # Get health check data
                    try:
                        health_result = await self.check_ptp_health({"check_config": True, "check_sync": True, "check_logs": True, "kubeconfig": kubeconfig})
                        data["health"] = health_result
                    except Exception as e:
                        data["health"] = {"error": str(e)}

            # Generate response
            response = self.query_engine.generate_response(query_info, data)

            return {
                "success": True,
                "question": question,
                "query_info": query_info,
                "response": response,
                "data": data
            }

        except Exception as e:
            logger.error(f"Error processing PTP query: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "question": arguments.get("question", ""),
                "suggestions": self.query_engine.suggest_queries()
            }

    async def analyze_servo_stability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze PI servo controller behavior and stability"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            lines = arguments.get("lines", 1000)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get logs
                logs = await self.log_parser.get_ptp_logs(namespace, lines, kubeconfig_path=kubeconfig_path)

                # Extract servo statistics
                servo_stats = self.log_parser.extract_servo_statistics(logs)

                # Generate recommendations based on analysis
                recommendations = []
                if servo_stats["stability"] == "unstable":
                    recommendations.append("Check for multiple daemon instances modifying the same clock")
                    recommendations.append("Review power management settings (C-states)")
                    recommendations.append("Consider adjusting step_threshold in ptp4lConf")
                elif servo_stats["stability"] == "degraded":
                    recommendations.append("Monitor for continued degradation")
                    recommendations.append("Check grandmaster stability")

                if servo_stats["clockcheck_events"]:
                    recommendations.append(f"Detected {len(servo_stats['clockcheck_events'])} clockcheck events - investigate frequency changes")

                result = {
                    "success": True,
                    "servo_state": servo_stats["servo_state"],
                    "stability": servo_stats["stability"],
                    "offset_stats": servo_stats["offset_stats"],
                    "frequency_stats": servo_stats["frequency_stats"],
                    "clockcheck_events": servo_stats["clockcheck_events"],
                    "recommendations": recommendations
                }
                if "components" in servo_stats:
                    result["components"] = servo_stats["components"]
                return result

        except Exception as e:
            logger.error(f"Error analyzing servo stability: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stability": "unknown"
            }

    async def analyze_frequency_drift(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Detect and trend frequency adjustments"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            lines = arguments.get("lines", 1000)
            window_minutes = arguments.get("window_minutes", 60)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                logs = await self.log_parser.get_ptp_logs(namespace, lines, kubeconfig_path=kubeconfig_path)
                freq_trend = self.log_parser.extract_frequency_trend(logs, window_minutes)

                estimated_stability = "unknown"
                if freq_trend["drift_rate_ppb_per_hour"] is not None:
                    drift = abs(freq_trend["drift_rate_ppb_per_hour"])
                    if drift < 100:
                        estimated_stability = "good"
                    elif drift < 1000:
                        estimated_stability = "moderate"
                    else:
                        estimated_stability = "poor"

                return {
                    "success": True,
                    "current_frequency_ppb": freq_trend["current_frequency_ppb"],
                    "drift_rate_ppb_per_hour": freq_trend["drift_rate_ppb_per_hour"],
                    "trend": freq_trend["trend"],
                    "sudden_changes": freq_trend["sudden_changes"],
                    "estimated_stability": estimated_stability,
                    "recent_samples": freq_trend["samples"]
                }

        except Exception as e:
            logger.error(f"Error analyzing frequency drift: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "trend": "unknown"
            }

    async def analyze_holdover(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Track and analyze holdover behavior"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            lines = arguments.get("lines", 2000)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                logs = await self.log_parser.get_ptp_logs(namespace, lines, kubeconfig_path=kubeconfig_path)
                holdover_data = self.log_parser.extract_holdover_events(logs)

                try:
                    config_data = await self.config_parser.get_ptp_configs(namespace, kubeconfig_path=kubeconfig_path)
                    ptp_config = self.model.create_ptp_configuration(config_data)
                    holdover_timeout = ptp_config.thresholds.get("holdOverTimeout", 0)
                except Exception as e:
                    logger.debug(f"Could not get holdover timeout from config: {e}")
                    holdover_timeout = None

                return {
                    "success": True,
                    "in_holdover": holdover_data["in_holdover"],
                    "holdover_duration_seconds": holdover_data["current_holdover_duration_seconds"],
                    "holdover_events": holdover_data["holdover_events"],
                    "total_holdover_time_seconds": holdover_data["total_holdover_time_seconds"],
                    "holdover_timeout_configured": holdover_timeout
                }

        except Exception as e:
            logger.error(f"Error analyzing holdover: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "in_holdover": False
            }

    async def get_gnss_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed GNSS receiver status and quality metrics"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            lines = arguments.get("lines", 1000)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                logs = await self.log_parser.get_ptp_logs(namespace, lines, kubeconfig_path=kubeconfig_path)
                gnss_status = self.log_parser.extract_gnss_status(logs)

                return {
                    "success": True,
                    **gnss_status
                }

        except Exception as e:
            logger.error(f"Error getting GNSS status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "gnss_available": False
            }

    async def get_port_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PTP port states and transition history"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            interface = arguments.get("interface")
            include_history = arguments.get("include_history", True)
            lines = arguments.get("lines", 1000)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get logs
                logs = await self.log_parser.get_ptp_logs(namespace, lines, kubeconfig_path=kubeconfig_path)

                # Extract port transitions from logs
                port_data = self.log_parser.extract_port_transitions(logs)

                if interface:
                    filtered_transitions = [t for t in port_data["transitions"] if t.get("port") == interface]
                    port_data["transitions"] = filtered_transitions

                result = {
                    "success": True,
                    "ports": port_data["ports"],
                    "current_states": port_data["current_states"],
                    "current_port_state": None,
                    "port_identity": None
                }

                # Get current port state from PMC (more reliable than logs for current state)
                try:
                    pmc_result = await self.run_pmc_query({"command": "PORT_DATA_SET", "namespace": namespace, "kubeconfig": kubeconfig})
                    if pmc_result.get("success") and pmc_result.get("data"):
                        pmc_data = pmc_result["data"]
                        result["current_port_state"] = pmc_data.get("port_state")
                        result["port_identity"] = pmc_data.get("port_identity")
                        result["delay_mechanism"] = pmc_data.get("delay_mechanism")
                        result["log_sync_interval"] = pmc_data.get("log_sync_interval")
                        result["log_announce_interval"] = pmc_data.get("log_announce_interval")
                except Exception as pmc_error:
                    logger.debug(f"Could not get port state from PMC: {pmc_error}")

                if include_history:
                    result["transitions"] = port_data["transitions"][-50:]  # Last 50 transitions

                # Add explanation if no transitions found
                if not port_data["transitions"]:
                    result["note"] = "No port state transitions found in recent logs. This is normal for a stable PTP system where port state hasn't changed."

                return result

        except Exception as e:
            logger.error(f"Error getting port status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "ports": {}
            }

    async def run_pmc_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PMC (PTP Management Client) queries for real-time data"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            command = arguments.get("command", "PARENT_DATA_SET")
            config_file = arguments.get("config_file", "/var/run/ptp4l.0.config")
            kubeconfig = arguments.get("kubeconfig")

            valid_commands = [
                "PARENT_DATA_SET",
                "DEFAULT_DATA_SET",
                "CURRENT_DATA_SET",
                "TIME_PROPERTIES_DATA_SET",
                "PORT_DATA_SET",
                "GRANDMASTER_SETTINGS_NP"
            ]

            if command not in valid_commands:
                return {
                    "success": False,
                    "error": f"Invalid PMC command. Valid commands: {valid_commands}",
                    "data": {}
                }

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get pod name
                pod_cmd = build_oc_command(kubeconfig_path)
                pod_cmd.extend([
                    "get", "pods", "-n", namespace,
                    "-l", "app=linuxptp-daemon",
                    "-o", "jsonpath={.items[0].metadata.name}"
                ])
                pod_result = subprocess.run(pod_cmd, capture_output=True, text=True, timeout=30)
                if pod_result.returncode != 0:
                    raise Exception(f"Failed to get pod name: {pod_result.stderr}")

                pod_name = pod_result.stdout.strip()

                # Execute PMC command
                pmc_cmd = build_oc_command(kubeconfig_path)
                pmc_cmd.extend([
                    "exec", "-n", namespace, pod_name,
                    "-c", "linuxptp-daemon-container", "--",
                    "pmc", "-u", "-b", "0", "-f", config_file, f"GET {command}"
                ])
                pmc_result = subprocess.run(pmc_cmd, capture_output=True, text=True, timeout=30)

            if pmc_result.returncode != 0:
                raise Exception(f"PMC command failed: {pmc_result.stderr}")

            # Parse PMC output
            parsed_data = self.log_parser.parse_pmc_output(pmc_result.stdout)

            return {
                "success": True,
                "command": command,
                "raw_output": pmc_result.stdout,
                **parsed_data
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "PMC query timed out",
                "data": {}
            }
        except Exception as e:
            logger.error(f"Error running PMC query: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }

    async def get_ptp_hardware_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PTP hardware capabilities for network interfaces in daemon pods"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            interface = arguments.get("interface")
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                # Get pod name
                pod_name = self._get_daemon_pod(namespace, kubeconfig_path)

                # Get list of interfaces to check
                if interface:
                    interfaces = [interface]
                else:
                    interfaces = self._get_physical_interfaces(pod_name, namespace, kubeconfig_path)

                results = []
                for iface in interfaces:
                    info = self._get_interface_ptp_info(pod_name, namespace, iface, kubeconfig_path)
                    results.append(info)

            return {
                "success": True,
                "interfaces": results,
                "total_interfaces": len(results),
                "ptp_capable_count": sum(1 for r in results if r.get("ptp_capable")),
                "hw_timestamping_count": sum(1 for r in results if r.get("hw_timestamping"))
            }

        except Exception as e:
            logger.error(f"Error getting PTP hardware info: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "interfaces": []
            }

    def _get_daemon_pod(self, namespace: str, kubeconfig_path: str = None) -> str:
        """Get the first linuxptp daemon pod name"""
        cmd = build_oc_command(kubeconfig_path)
        cmd.extend([
            "get", "pods", "-n", namespace,
            "-l", "app=linuxptp-daemon",
            "-o", "jsonpath={.items[0].metadata.name}"
        ])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"Failed to get daemon pod: {result.stderr}")
        return result.stdout.strip()

    def _exec_in_pod(self, pod_name: str, namespace: str, command: List[str],
                     kubeconfig_path: str = None, timeout: int = 15) -> str:
        """Execute a command in the linuxptp daemon container"""
        cmd = build_oc_command(kubeconfig_path)
        cmd.extend([
            "exec", "-n", namespace, pod_name,
            "-c", "linuxptp-daemon-container", "--"
        ])
        cmd.extend(command)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout

    def _get_physical_interfaces(self, pod_name: str, namespace: str,
                                 kubeconfig_path: str = None) -> List[str]:
        """Get list of physical network interfaces (excluding virtual ones)"""
        try:
            output = self._exec_in_pod(
                pod_name, namespace,
                ["ip", "-o", "link", "show"],
                kubeconfig_path
            )
            virtual_prefixes = ("lo", "docker", "veth", "br-", "virbr", "cni", "flannel", "ovs", "tun", "tap")
            interfaces = []
            for line in output.strip().split('\n'):
                match = re.match(r'\d+:\s+(\S+?)(?:@\S+)?:', line)
                if match:
                    name = match.group(1)
                    if not name.startswith(virtual_prefixes) and len(interfaces) < 20:
                        interfaces.append(name)
            return interfaces
        except Exception:
            return []

    def _get_interface_ptp_info(self, pod_name: str, namespace: str, iface: str,
                                kubeconfig_path: str = None) -> Dict[str, Any]:
        """Get PTP-specific hardware info for a single interface"""
        info = {
            "name": iface,
            "ptp_capable": False,
            "hw_timestamping": False,
            "sw_timestamping": False,
            "phc_device": None,
            "driver": None,
            "firmware_version": None,
            "bus_info": None,
            "speed": None,
            "timestamping_capabilities": {},
            "ptp_assessment": "unknown"
        }

        # Get timestamping capabilities via ethtool -T
        try:
            ts_output = self._exec_in_pod(
                pod_name, namespace,
                ["ethtool", "-T", iface],
                kubeconfig_path
            )
            info.update(self._parse_ethtool_timestamping(ts_output))
        except Exception as e:
            info["timestamping_error"] = str(e)

        # Get driver info via ethtool -i
        try:
            driver_output = self._exec_in_pod(
                pod_name, namespace,
                ["ethtool", "-i", iface],
                kubeconfig_path
            )
            info.update(self._parse_ethtool_driver(driver_output))
        except Exception:
            pass

        # Get link speed
        try:
            speed_output = self._exec_in_pod(
                pod_name, namespace,
                ["ethtool", iface],
                kubeconfig_path
            )
            speed_match = re.search(r'Speed:\s*(\S+)', speed_output)
            if speed_match:
                info["speed"] = speed_match.group(1)
        except Exception:
            pass

        # Assess PTP readiness
        info["ptp_assessment"] = self._assess_ptp_readiness(info)

        return info

    def _parse_ethtool_timestamping(self, output: str) -> Dict[str, Any]:
        """Parse ethtool -T output for timestamping capabilities"""
        result = {
            "ptp_capable": False,
            "hw_timestamping": False,
            "sw_timestamping": False,
            "phc_device": None,
            "timestamping_capabilities": {
                "hardware_transmit": False,
                "hardware_receive_all": False,
                "hardware_receive_filter_ptp_v2": False,
                "software_transmit": False,
                "software_receive": False,
            }
        }

        current_section = None
        for line in output.split('\n'):
            line_stripped = line.strip()

            if "Capabilities:" in line:
                current_section = "capabilities"
                continue
            elif "PTP Hardware Clock:" in line:
                match = re.search(r'PTP Hardware Clock:\s*(\d+)', line)
                if match:
                    phc_index = int(match.group(1))
                    result["phc_device"] = f"/dev/ptp{phc_index}"
                    result["ptp_capable"] = True
                current_section = None
                continue

            if current_section == "capabilities" and line_stripped:
                cap_lower = line_stripped.lower()
                if "hardware-transmit" in cap_lower:
                    result["timestamping_capabilities"]["hardware_transmit"] = True
                    result["hw_timestamping"] = True
                elif "hardware-receive" in cap_lower:
                    if "all" in cap_lower:
                        result["timestamping_capabilities"]["hardware_receive_all"] = True
                    if "ptp" in cap_lower and "v2" in cap_lower:
                        result["timestamping_capabilities"]["hardware_receive_filter_ptp_v2"] = True
                    result["hw_timestamping"] = True
                elif "software-transmit" in cap_lower:
                    result["timestamping_capabilities"]["software_transmit"] = True
                    result["sw_timestamping"] = True
                elif "software-receive" in cap_lower:
                    result["timestamping_capabilities"]["software_receive"] = True
                    result["sw_timestamping"] = True

        return result

    def _parse_ethtool_driver(self, output: str) -> Dict[str, Any]:
        """Parse ethtool -i output for driver information"""
        result = {}
        for line in output.split('\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                if key == "driver":
                    result["driver"] = value
                elif key == "version":
                    result["driver_version"] = value
                elif key == "firmware-version":
                    result["firmware_version"] = value
                elif key == "bus-info":
                    result["bus_info"] = value
        return result

    def _assess_ptp_readiness(self, info: Dict[str, Any]) -> str:
        """Assess PTP readiness based on hardware capabilities"""
        if info.get("hw_timestamping") and info.get("phc_device"):
            caps = info.get("timestamping_capabilities", {})
            if caps.get("hardware_transmit") and (caps.get("hardware_receive_all") or caps.get("hardware_receive_filter_ptp_v2")):
                return "fully_capable"
            return "partial_hw_support"
        elif info.get("sw_timestamping"):
            return "software_only"
        elif info.get("ptp_capable"):
            return "capable_no_hw_timestamps"
        return "not_capable"

    async def map_hardware_to_config(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Map PTP configurations to actual hardware capabilities and identify misconfigurations"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            kubeconfig = arguments.get("kubeconfig")

            # Get PTP configurations
            config_data = await self.config_parser.get_ptp_configs(namespace, kubeconfig)
            ptp_config = self.model.create_ptp_configuration(config_data)

            # Extract configured interfaces from profiles
            configured_interfaces = []
            for profile in ptp_config.profiles:
                ptp4l_conf = profile.get("ptp4lConf", {})
                interfaces = ptp4l_conf.get("interfaces", {})
                ptp4l_opts = profile.get("ptp4lOpts", "")

                for iface_name, iface_config in interfaces.items():
                    configured_interfaces.append({
                        "name": iface_name,
                        "profile": profile.get("name", "unknown"),
                        "master_only": iface_config.get("masterOnly", False),
                        "config": iface_config
                    })

                # Also check ptp4lOpts for -i flag interfaces
                if "-i " in ptp4l_opts:
                    for match in re.finditer(r'-i\s+(\S+)', ptp4l_opts):
                        iface_name = match.group(1)
                        if not any(ci["name"] == iface_name for ci in configured_interfaces):
                            configured_interfaces.append({
                                "name": iface_name,
                                "profile": profile.get("name", "unknown"),
                                "master_only": False,
                                "config": {},
                                "source": "ptp4lOpts"
                            })

            if not configured_interfaces:
                return {
                    "success": True,
                    "mappings": [],
                    "issues": ["No interfaces found in PTP configuration profiles"],
                    "warnings": [],
                    "summary": "No configured interfaces to map"
                }

            # Get hardware capabilities for each configured interface
            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                pod_name = self._get_daemon_pod(namespace, kubeconfig_path)

                mappings = []
                issues = []
                warnings = []

                for ci in configured_interfaces:
                    iface_name = ci["name"]
                    hw_info = self._get_interface_ptp_info(pod_name, namespace, iface_name, kubeconfig_path)

                    mapping = {
                        "interface": iface_name,
                        "profile": ci["profile"],
                        "master_only": ci["master_only"],
                        "hardware": {
                            "ptp_capable": hw_info.get("ptp_capable", False),
                            "hw_timestamping": hw_info.get("hw_timestamping", False),
                            "phc_device": hw_info.get("phc_device"),
                            "driver": hw_info.get("driver"),
                            "speed": hw_info.get("speed"),
                            "ptp_assessment": hw_info.get("ptp_assessment", "unknown")
                        },
                        "status": "ok"
                    }

                    # Check for misconfigurations
                    if not hw_info.get("ptp_capable", False):
                        mapping["status"] = "error"
                        issues.append(
                            f"Interface '{iface_name}' (profile: {ci['profile']}) is configured "
                            f"for PTP but does NOT have PTP hardware support"
                        )
                    elif not hw_info.get("hw_timestamping", False):
                        mapping["status"] = "warning"
                        warnings.append(
                            f"Interface '{iface_name}' (profile: {ci['profile']}) has a PHC device "
                            f"but lacks hardware timestamping — PTP will use software timestamps "
                            f"with reduced accuracy"
                        )
                    elif hw_info.get("ptp_assessment") == "partial_hw_support":
                        mapping["status"] = "warning"
                        warnings.append(
                            f"Interface '{iface_name}' (profile: {ci['profile']}) has partial "
                            f"hardware timestamping support — check receive filter capabilities"
                        )

                    if hw_info.get("timestamping_error"):
                        mapping["hardware"]["timestamping_error"] = hw_info["timestamping_error"]

                    mappings.append(mapping)

            error_count = sum(1 for m in mappings if m["status"] == "error")
            warn_count = sum(1 for m in mappings if m["status"] == "warning")

            summary = f"{len(mappings)} interface(s) mapped"
            if error_count:
                summary += f", {error_count} misconfiguration(s) found"
            if warn_count:
                summary += f", {warn_count} warning(s)"
            if not error_count and not warn_count:
                summary += ", all hardware capabilities verified"

            return {
                "success": True,
                "mappings": mappings,
                "issues": issues,
                "warnings": warnings,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Error mapping hardware to config: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "mappings": []
            }

    async def get_ptp_metrics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch and analyze Prometheus metrics from PTP daemon pods"""
        try:
            namespace = arguments.get("namespace", "openshift-ptp")
            metric_filter = arguments.get("filter")
            include_summary = arguments.get("include_summary", True)
            kubeconfig = arguments.get("kubeconfig")

            with kubeconfig_from_base64(kubeconfig) as kubeconfig_path:
                pod_name = self._get_daemon_pod(namespace, kubeconfig_path)

                # Fetch metrics from port 9091
                raw_metrics = self._exec_in_pod(
                    pod_name, namespace,
                    ["curl", "-s", "--max-time", "5", "http://localhost:9091/metrics"],
                    kubeconfig_path,
                    timeout=20
                )

            # Parse Prometheus text format
            metrics = self._parse_prometheus_metrics(raw_metrics)

            # Filter to PTP-related metrics
            ptp_metrics = [m for m in metrics if self._is_ptp_metric(m["name"])]

            # Apply user filter if specified
            if metric_filter:
                filter_lower = metric_filter.lower()
                ptp_metrics = [
                    m for m in ptp_metrics
                    if filter_lower in m["name"].lower() or
                    any(filter_lower in str(v).lower() for v in m.get("labels", {}).values())
                ]

            result = {
                "success": True,
                "total_metrics_scraped": len(metrics),
                "ptp_metrics_count": len(ptp_metrics),
                "metrics": ptp_metrics
            }

            if include_summary and ptp_metrics:
                result["summary"] = self._summarize_ptp_metrics(ptp_metrics)

            return result

        except Exception as e:
            logger.error(f"Error getting PTP metrics: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "metrics": []
            }

    def _parse_prometheus_metrics(self, raw: str) -> List[Dict[str, Any]]:
        """Parse Prometheus text exposition format into structured metrics"""
        metrics = []
        help_texts = {}
        type_info = {}

        for line in raw.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # Parse HELP lines
            if line.startswith("# HELP "):
                parts = line[7:].split(' ', 1)
                if len(parts) == 2:
                    help_texts[parts[0]] = parts[1]
                continue

            # Parse TYPE lines
            if line.startswith("# TYPE "):
                parts = line[7:].split(' ', 1)
                if len(parts) == 2:
                    type_info[parts[0]] = parts[1]
                continue

            # Skip other comments
            if line.startswith("#"):
                continue

            # Parse metric lines: metric_name{label="value",...} value
            match = re.match(r'(\w+)(\{[^}]*\})?\s+([\d.eE+\-]+(?:nan)?)', line, re.IGNORECASE)
            if match:
                name = match.group(1)
                labels_str = match.group(2)
                value_str = match.group(3)

                try:
                    value = float(value_str)
                except ValueError:
                    continue

                labels = {}
                if labels_str:
                    for label_match in re.finditer(r'(\w+)="([^"]*)"', labels_str):
                        labels[label_match.group(1)] = label_match.group(2)

                metrics.append({
                    "name": name,
                    "labels": labels,
                    "value": value,
                    "help": help_texts.get(name),
                    "type": type_info.get(name)
                })

        return metrics

    def _is_ptp_metric(self, name: str) -> bool:
        """Check if a metric name is PTP-related"""
        ptp_prefixes = (
            "openshift_ptp_", "ptp4l_", "phc2sys_", "ts2phc_",
            "clock_", "dpll_", "gnss_", "npu_",
        )
        ptp_keywords = (
            "offset", "frequency", "delay", "clock_class",
            "clock_state", "sync", "holdover", "servo",
            "interface_role", "ptp",
        )
        name_lower = name.lower()
        return (name_lower.startswith(ptp_prefixes) or
                any(kw in name_lower for kw in ptp_keywords))

    def _summarize_ptp_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from PTP metrics"""
        summary = {
            "metric_names": sorted(set(m["name"] for m in metrics)),
            "by_metric": {}
        }

        # Group metrics by name
        grouped = {}
        for m in metrics:
            grouped.setdefault(m["name"], []).append(m)

        for name, group in grouped.items():
            values = [m["value"] for m in group]
            entry = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
            }

            # Include labels from first sample for context
            if group[0].get("labels"):
                label_keys = list(group[0]["labels"].keys())
                entry["label_keys"] = label_keys

                # If there are interface_role or node labels, group by them
                for key in ("interface_role", "node", "iface", "process"):
                    distinct = set(m["labels"].get(key) for m in group if key in m.get("labels", {}))
                    if distinct:
                        entry[f"distinct_{key}s"] = sorted(distinct)

            summary["by_metric"][name] = entry

        return summary
