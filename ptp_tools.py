#!/usr/bin/env python3
"""
PTP Tools - Implementation of MCP tools for PTP monitoring
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ptp_config_parser import PTPConfigParser
from ptp_log_parser import PTPLogParser
from ptp_model import PTPModel
from ptp_query_engine import PTPQueryEngine

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
            
            # Get raw configuration
            config_data = await self.config_parser.get_ptp_configs(namespace)
            
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
            
            # Get logs
            logs = await self.log_parser.get_ptp_logs(namespace, lines, since)
            
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
                        "timestamp": log.timestamp.isoformat(),
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
            
            # Get logs first
            logs = await self.log_parser.get_ptp_logs()
            
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
                        "timestamp": log.timestamp.isoformat(),
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
            
            # Get logs to extract grandmaster info
            logs = await self.log_parser.get_ptp_logs()
            gm_info = self.log_parser.extract_grandmaster_info(logs)
            
            # Get configuration for additional context
            config_data = await self.config_parser.get_ptp_configs()
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
            
            # Get logs and configuration
            logs = await self.log_parser.get_ptp_logs()
            config_data = await self.config_parser.get_ptp_configs()
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
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing sync status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sync_status": {"dpll_locked": False, "offset_in_range": False}
            }
    
    async def get_clock_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get current clock hierarchy"""
        try:
            include_ports = arguments.get("include_ports", True)
            include_priorities = arguments.get("include_priorities", True)
            
            # Get logs and configuration
            logs = await self.log_parser.get_ptp_logs()
            config_data = await self.config_parser.get_ptp_configs()
            ptp_config = self.model.create_ptp_configuration(config_data)
            
            # Get clock hierarchy
            hierarchy = self.model.get_clock_hierarchy(ptp_config, logs)
            
            # Add log-based hierarchy info
            log_hierarchy = self.log_parser.extract_clock_hierarchy(logs)
            hierarchy.update(log_hierarchy)
            
            result = {
                "success": True,
                "hierarchy": hierarchy
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
    
    async def check_ptp_health(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive PTP health check"""
        try:
            check_config = arguments.get("check_config", True)
            check_sync = arguments.get("check_sync", True)
            check_logs = arguments.get("check_logs", True)
            
            health_result = {
                "success": True,
                "overall_status": "unknown",
                "checks": {}
            }
            
            # Check configuration
            if check_config:
                try:
                    config_data = await self.config_parser.get_ptp_configs()
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
                    logs = await self.log_parser.get_ptp_logs()
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
                    logs = await self.log_parser.get_ptp_logs()
                    
                    # Look for error and warning messages
                    error_logs = [log for log in logs if log.level == "error"]
                    warning_logs = [log for log in logs if log.level == "warning"]
                    
                    health_result["checks"]["logs"] = {
                        "total_logs": len(logs),
                        "error_count": len(error_logs),
                        "warning_count": len(warning_logs),
                        "recent_errors": [
                            {
                                "timestamp": log.timestamp.isoformat(),
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
            
            if query_info["query_type"] in ["grandmaster", "configuration", "sync_status", "clock_hierarchy", "health_check"]:
                # Get configuration data
                try:
                    config_data = await self.config_parser.get_ptp_configs()
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
                    logs = await self.log_parser.get_ptp_logs()
                    data["grandmaster"] = self.log_parser.extract_grandmaster_info(logs)
                    data["sync_status"] = self.log_parser.extract_sync_status(logs)
                    data["clock_hierarchy"] = self.log_parser.extract_clock_hierarchy(logs)
                    data["offset_trend"] = self.model.get_offset_trend(logs, query_info.get("time_range"))
                except Exception as e:
                    data["logs"] = {"error": str(e)}
            
            if query_info["query_type"] == "itu_compliance":
                # Get configuration for ITU compliance check
                try:
                    config_data = await self.config_parser.get_ptp_configs()
                    ptp_config = self.model.create_ptp_configuration(config_data)
                    data["itu_compliance"] = self.model.validate_itu_t_compliance(ptp_config)
                except Exception as e:
                    data["itu_compliance"] = {"error": str(e)}
            
            if query_info["query_type"] == "health_check":
                # Get health check data
                try:
                    health_result = await self.check_ptp_health({"check_config": True, "check_sync": True, "check_logs": True})
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