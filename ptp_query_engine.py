#!/usr/bin/env python3
"""
PTP Query Engine - Natural language processing for PTP queries
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PTPQueryEngine:
    """Natural language query engine for PTP information"""
    
    def __init__(self):
        # Query patterns for different types of questions
        self.query_patterns = {
            "grandmaster": [
                r"what is the current grandmaster",
                r"who is the grandmaster",
                r"show grandmaster",
                r"grandmaster status",
                r"current gm"
            ],
            "configuration": [
                r"show ptpconfig parameters",
                r"ptp configuration",
                r"ptpconfig",
                r"configuration parameters",
                r"show config"
            ],
            "sync_status": [
                r"check for sync loss",
                r"sync status",
                r"synchronization status",
                r"is it synced",
                r"sync health"
            ],
            "clock_hierarchy": [
                r"clock hierarchy",
                r"show clock hierarchy",
                r"clock topology",
                r"clock structure"
            ],
            "offset_trend": [
                r"offset trend",
                r"get offset trend",
                r"offset analysis",
                r"frequency offset"
            ],
            "bmca_state": [
                r"bmca state",
                r"best master clock",
                r"master clock algorithm",
                r"bmca status"
            ],
            "clock_class": [
                r"clockclass change",
                r"clock class",
                r"clockclass",
                r"class change"
            ],
            "logs_search": [
                r"search logs",
                r"log search",
                r"find in logs",
                r"log analysis"
            ],
            "health_check": [
                r"health check",
                r"ptp health",
                r"system health",
                r"diagnostics"
            ],
            "itu_compliance": [
                r"itu compliance",
                r"g\.8275\.1",
                r"itu-t",
                r"compliance check"
            ]
        }
        
        # Time range patterns
        self.time_patterns = {
            "last_hour": [
                r"last hour",
                r"past hour",
                r"in the last hour"
            ],
            "last_day": [
                r"last day",
                r"past day",
                r"in the last day",
                r"yesterday"
            ],
            "last_week": [
                r"last week",
                r"past week",
                r"in the last week"
            ],
            "custom_time": [
                r"last (\d+) (minutes?|hours?|days?)",
                r"past (\d+) (minutes?|hours?|days?)",
                r"(\d+) (minutes?|hours?|days?) ago"
            ]
        }
    
    def parse_query(self, question: str, context: str = None) -> Dict[str, Any]:
        """Parse natural language query into structured format"""
        question_lower = question.lower().strip()
        
        # Determine query type
        query_type = self._determine_query_type(question_lower)
        
        # Extract time range if present
        time_range = self._extract_time_range(question_lower)
        
        # Extract specific parameters
        parameters = self._extract_parameters(question_lower)
        
        return {
            "original_question": question,
            "context": context,
            "query_type": query_type,
            "time_range": time_range,
            "parameters": parameters,
            "parsed_at": datetime.now().isoformat()
        }
    
    def _determine_query_type(self, question: str) -> str:
        """Determine the type of query being asked"""
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question, re.IGNORECASE):
                    return query_type
        
        # Default to general query
        return "general"
    
    def _extract_time_range(self, question: str) -> Optional[str]:
        """Extract time range from question"""
        # Check for specific time ranges
        for time_range, patterns in self.time_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question, re.IGNORECASE):
                    return time_range
        
        # Check for custom time ranges
        custom_match = re.search(r"last (\d+) (minutes?|hours?|days?)", question, re.IGNORECASE)
        if custom_match:
            amount = custom_match.group(1)
            unit = custom_match.group(2)
            if unit.startswith("minute"):
                return f"last_{amount}m"
            elif unit.startswith("hour"):
                return f"last_{amount}h"
            elif unit.startswith("day"):
                return f"last_{amount}d"
        
        return None
    
    def _extract_parameters(self, question: str) -> Dict[str, Any]:
        """Extract specific parameters from the question"""
        parameters = {}
        
        # Extract log level if mentioned
        log_levels = ["error", "warning", "info", "debug"]
        for level in log_levels:
            if level in question:
                parameters["log_level"] = level
                break
        
        # Extract specific components
        components = ["ptp4l", "phc2sys", "ts2phc", "dpll", "gnss", "gm"]
        for component in components:
            if component in question:
                parameters["component"] = component
                break
        
        # Extract specific interfaces
        interface_match = re.search(r"interface (\w+)", question, re.IGNORECASE)
        if interface_match:
            parameters["interface"] = interface_match.group(1)
        
        # Extract specific values
        value_match = re.search(r"(\d+)", question)
        if value_match:
            parameters["value"] = int(value_match.group(1))
        
        return parameters
    
    def generate_response(self, query_info: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Generate natural language response based on query and data"""
        query_type = query_info["query_type"]
        
        if query_type == "grandmaster":
            return self._generate_grandmaster_response(data)
        elif query_type == "configuration":
            return self._generate_configuration_response(data)
        elif query_type == "sync_status":
            return self._generate_sync_status_response(data)
        elif query_type == "clock_hierarchy":
            return self._generate_clock_hierarchy_response(data)
        elif query_type == "offset_trend":
            return self._generate_offset_trend_response(data)
        elif query_type == "bmca_state":
            return self._generate_bmca_state_response(data)
        elif query_type == "health_check":
            return self._generate_health_check_response(data)
        elif query_type == "itu_compliance":
            return self._generate_itu_compliance_response(data)
        else:
            return self._generate_general_response(data)
    
    def _generate_grandmaster_response(self, data: Dict[str, Any]) -> str:
        """Generate response for grandmaster queries"""
        gm_info = data.get("grandmaster", {})
        
        if not gm_info or gm_info.get("status") == "unknown":
            return "No grandmaster information available in the current logs."
        
        status = gm_info.get("status", "unknown")
        interface = gm_info.get("interface", "unknown")
        offset = gm_info.get("offset")
        frequency = gm_info.get("frequency")
        last_seen = gm_info.get("last_seen")
        
        response = f"Current grandmaster status: {status}"
        if interface != "unknown":
            response += f" on interface {interface}"
        
        if offset is not None:
            response += f"\nCurrent offset: {offset} ns"
        
        if frequency is not None:
            response += f"\nFrequency adjustment: {frequency} ppb"
        
        if last_seen:
            response += f"\nLast seen: {last_seen}"
        
        return response
    
    def _generate_configuration_response(self, data: Dict[str, Any]) -> str:
        """Generate response for configuration queries"""
        config = data.get("configuration", {})
        
        if not config:
            return "No PTP configuration found."
        
        response = "PTP Configuration:\n"
        
        # Basic info
        name = config.get("name", "unknown")
        clock_type = config.get("clock_type", "unknown")
        domain = config.get("domain", "unknown")
        
        response += f"- Name: {name}\n"
        response += f"- Clock Type: {clock_type}\n"
        response += f"- Domain: {domain}\n"
        
        # Priorities
        priorities = config.get("priorities", {})
        if priorities:
            response += "- Priorities:\n"
            for priority_name, priority_value in priorities.items():
                response += f"  - {priority_name}: {priority_value}\n"
        
        # Clock class
        clock_class = config.get("clock_class")
        if clock_class is not None:
            response += f"- Clock Class: {clock_class}\n"
        
        # Sync intervals
        sync_intervals = config.get("sync_intervals", {})
        if sync_intervals:
            response += "- Sync Intervals:\n"
            for interval_name, interval_value in sync_intervals.items():
                response += f"  - {interval_name}: {interval_value}\n"
        
        return response
    
    def _generate_sync_status_response(self, data: Dict[str, Any]) -> str:
        """Generate response for sync status queries"""
        sync_status = data.get("sync_status", {})
        
        if not sync_status:
            return "No synchronization status information available."
        
        response = "Synchronization Status:\n"
        
        dpll_locked = sync_status.get("dpll_locked", False)
        gnss_available = sync_status.get("gnss_available", False)
        offset_in_range = sync_status.get("offset_in_range", False)
        last_offset = sync_status.get("last_offset")
        
        response += f"- DPLL Locked: {'Yes' if dpll_locked else 'No'}\n"
        response += f"- GNSS Available: {'Yes' if gnss_available else 'No'}\n"
        response += f"- Offset in Range: {'Yes' if offset_in_range else 'No'}\n"
        
        if last_offset is not None:
            response += f"- Last Offset: {last_offset} ns\n"
        
        # Overall status
        if dpll_locked and offset_in_range:
            response += "\nStatus: HEALTHY - Clock is synchronized"
        elif dpll_locked and not offset_in_range:
            response += "\nStatus: WARNING - Clock is locked but offset is out of range"
        else:
            response += "\nStatus: UNHEALTHY - Clock is not synchronized"
        
        return response
    
    def _generate_clock_hierarchy_response(self, data: Dict[str, Any]) -> str:
        """Generate response for clock hierarchy queries"""
        hierarchy = data.get("clock_hierarchy", {})
        
        if not hierarchy:
            return "No clock hierarchy information available."
        
        response = "Clock Hierarchy:\n"
        
        current_clock = hierarchy.get("current_clock", {})
        if current_clock:
            clock_type = current_clock.get("type", "unknown")
            domain = current_clock.get("domain", "unknown")
            clock_class = current_clock.get("clock_class", "unknown")
            
            response += f"- Current Clock: {clock_type} (Domain {domain}, Class {clock_class})\n"
        
        grandmaster = hierarchy.get("grandmaster")
        if grandmaster:
            response += f"- Grandmaster: Active (last seen: {grandmaster.get('last_seen')})\n"
        else:
            response += "- Grandmaster: Not detected\n"
        
        boundary_clocks = hierarchy.get("boundary_clocks", [])
        if boundary_clocks:
            response += f"- Boundary Clocks: {len(boundary_clocks)} detected\n"
        else:
            response += "- Boundary Clocks: None detected\n"
        
        return response
    
    def _generate_offset_trend_response(self, data: Dict[str, Any]) -> str:
        """Generate response for offset trend queries"""
        trend = data.get("offset_trend", {})
        
        if not trend:
            return "No offset trend information available."
        
        response = "Offset Trend Analysis:\n"
        
        current_offset = trend.get("current_offset")
        trend_direction = trend.get("trend", "unknown")
        min_offset = trend.get("min_offset")
        max_offset = trend.get("max_offset")
        average_offset = trend.get("average_offset")
        samples = trend.get("samples", 0)
        
        if current_offset is not None:
            response += f"- Current Offset: {current_offset} ns\n"
        
        response += f"- Trend: {trend_direction}\n"
        
        if min_offset is not None and max_offset is not None:
            response += f"- Range: {min_offset} to {max_offset} ns\n"
        
        if average_offset is not None:
            response += f"- Average: {average_offset} ns\n"
        
        response += f"- Samples: {samples}\n"
        
        return response
    
    def _generate_bmca_state_response(self, data: Dict[str, Any]) -> str:
        """Generate response for BMCA state queries"""
        bmca_state = data.get("bmca_state", {})
        
        if not bmca_state:
            return "No BMCA state information available."
        
        response = "BMCA (Best Master Clock Algorithm) State:\n"
        
        role = bmca_state.get("role", "unknown")
        domain = bmca_state.get("domain", "unknown")
        priority1 = bmca_state.get("priority1")
        priority2 = bmca_state.get("priority2")
        
        response += f"- Role: {role}\n"
        response += f"- Domain: {domain}\n"
        
        if priority1 is not None:
            response += f"- Priority 1: {priority1}\n"
        
        if priority2 is not None:
            response += f"- Priority 2: {priority2}\n"
        
        return response
    
    def _generate_health_check_response(self, data: Dict[str, Any]) -> str:
        """Generate response for health check queries"""
        health = data.get("health", {})
        
        if not health:
            return "No health check information available."
        
        response = "PTP Health Check:\n"
        
        config_valid = health.get("config_valid", False)
        sync_healthy = health.get("sync_healthy", False)
        logs_healthy = health.get("logs_healthy", False)
        
        response += f"- Configuration: {'Valid' if config_valid else 'Invalid'}\n"
        response += f"- Synchronization: {'Healthy' if sync_healthy else 'Unhealthy'}\n"
        response += f"- Logs: {'Healthy' if logs_healthy else 'Issues detected'}\n"
        
        # Overall status
        if config_valid and sync_healthy and logs_healthy:
            response += "\nOverall Status: HEALTHY"
        elif not config_valid:
            response += "\nOverall Status: CRITICAL - Configuration issues"
        elif not sync_healthy:
            response += "\nOverall Status: WARNING - Synchronization issues"
        else:
            response += "\nOverall Status: WARNING - Log issues detected"
        
        return response
    
    def _generate_itu_compliance_response(self, data: Dict[str, Any]) -> str:
        """Generate response for ITU compliance queries"""
        compliance = data.get("itu_compliance", {})
        
        if not compliance:
            return "No ITU-T G.8275.1 compliance information available."
        
        response = "ITU-T G.8275.1 Compliance Check:\n"
        
        compliant = compliance.get("compliant", False)
        warnings = compliance.get("warnings", [])
        errors = compliance.get("errors", [])
        
        response += f"- Compliant: {'Yes' if compliant else 'No'}\n"
        
        if warnings:
            response += "- Warnings:\n"
            for warning in warnings:
                response += f"  - {warning}\n"
        
        if errors:
            response += "- Errors:\n"
            for error in errors:
                response += f"  - {error}\n"
        
        if not warnings and not errors:
            response += "- No issues detected\n"
        
        return response
    
    def _generate_general_response(self, data: Dict[str, Any]) -> str:
        """Generate general response for unrecognized queries"""
        return f"Query processed. Available data: {json.dumps(data, indent=2)}"
    
    def suggest_queries(self, context: str = None) -> List[str]:
        """Suggest related queries based on context"""
        suggestions = [
            "What is the current grandmaster?",
            "Show ptpconfig parameters",
            "Check for sync loss",
            "Search logs for clockClass change",
            "Get offset trend in last hour",
            "What is the BMCA state?",
            "Show current clock hierarchy",
            "Check PTP health",
            "Validate ITU-T G.8275.1 compliance"
        ]
        
        return suggestions 