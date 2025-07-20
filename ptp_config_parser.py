#!/usr/bin/env python3
"""
PTP Configuration Parser - Parses OpenShift ptpconfig resources
"""

import json
import logging
import subprocess
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PTPConfigParser:
    """Parser for OpenShift PTP configuration resources"""
    
    def __init__(self):
        self.namespace = "openshift-ptp"
    
    async def get_ptp_configs(self, namespace: str = None) -> Dict[str, Any]:
        """Get all PTP configurations from OpenShift cluster"""
        if namespace is None:
            namespace = self.namespace
            
        try:
            # Execute oc command to get ptpconfig resources
            cmd = [
                "oc", "get", "ptpconfig", 
                "-n", namespace, 
                "-o", "yaml"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to get PTP configs: {result.stderr}")
            
            # Parse YAML response
            configs = yaml.safe_load(result.stdout)
            return self._parse_ptp_configs(configs)
            
        except subprocess.TimeoutExpired:
            raise Exception("Timeout getting PTP configurations")
        except Exception as e:
            logger.error(f"Error getting PTP configs: {str(e)}")
            raise
    
    def _parse_ptp_configs(self, raw_configs: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw PTP configurations into structured format"""
        parsed_configs = {
            "apiVersion": raw_configs.get("apiVersion"),
            "kind": raw_configs.get("kind"),
            "metadata": raw_configs.get("metadata", {}),
            "items": []
        }
        
        for item in raw_configs.get("items", []):
            parsed_item = self._parse_ptp_config_item(item)
            parsed_configs["items"].append(parsed_item)
        
        return parsed_configs
    
    def _parse_ptp_config_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse individual PTP configuration item"""
        parsed_item = {
            "metadata": item.get("metadata", {}),
            "spec": self._parse_ptp_spec(item.get("spec", {})),
            "status": item.get("status", {})
        }
        
        return parsed_item
    
    def _parse_ptp_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PTP specification section"""
        parsed_spec = {
            "profile": [],
            "recommend": []
        }
        
        # Parse profiles
        for profile in spec.get("profile", []):
            parsed_profile = self._parse_ptp_profile(profile)
            parsed_spec["profile"].append(parsed_profile)
        
        # Parse recommendations
        for recommend in spec.get("recommend", []):
            parsed_recommend = self._parse_ptp_recommend(recommend)
            parsed_spec["recommend"].append(parsed_recommend)
        
        return parsed_spec
    
    def _parse_ptp_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PTP profile configuration"""
        parsed_profile = {
            "name": profile.get("name"),
            "ptpSchedulingPolicy": profile.get("ptpSchedulingPolicy"),
            "ptpSchedulingPriority": profile.get("ptpSchedulingPriority"),
            "phc2sysOpts": profile.get("phc2sysOpts"),
            "ptp4lOpts": profile.get("ptp4lOpts"),
            "ptp4lConf": self._parse_ptp4l_conf(profile.get("ptp4lConf", "")),
            "ptpClockThreshold": self._parse_ptp_clock_threshold(profile.get("ptpClockThreshold", {}))
        }
        
        return parsed_profile
    
    def _parse_ptp4l_conf(self, conf_text: str) -> Dict[str, Any]:
        """Parse ptp4l configuration text into structured format"""
        if not conf_text:
            return {}
        
        parsed_conf = {
            "interfaces": {},
            "global": {},
            "servo": {},
            "transport": {},
            "clock": {}
        }
        
        current_section = "global"
        lines = conf_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Check for section headers
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1]
                if section_name in ["global", "servo", "transport", "clock"]:
                    current_section = section_name
                else:
                    # Interface section
                    current_section = "interfaces"
                    interface_name = section_name
                    if interface_name not in parsed_conf["interfaces"]:
                        parsed_conf["interfaces"][interface_name] = {}
                continue
            
            # Parse key-value pairs
            if ' ' in line:
                key, value = line.split(' ', 1)
                key = key.strip()
                value = value.strip()
                
                if current_section == "interfaces":
                    parsed_conf["interfaces"][interface_name][key] = self._parse_value(value)
                else:
                    parsed_conf[current_section][key] = self._parse_value(value)
        
        return parsed_conf
    
    def _parse_value(self, value: str) -> Any:
        """Parse configuration value with appropriate type"""
        # Try to parse as integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try to parse as boolean
        if value.lower() in ["true", "1", "yes"]:
            return True
        elif value.lower() in ["false", "0", "no"]:
            return False
        
        # Try to parse hex values
        if value.startswith("0x"):
            try:
                return int(value, 16)
            except ValueError:
                pass
        
        # Return as string
        return value
    
    def _parse_ptp_clock_threshold(self, threshold: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PTP clock threshold configuration"""
        return {
            "holdOverTimeout": threshold.get("holdOverTimeout"),
            "maxOffsetThreshold": threshold.get("maxOffsetThreshold"),
            "minOffsetThreshold": threshold.get("minOffsetThreshold")
        }
    
    def _parse_ptp_recommend(self, recommend: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PTP recommendation configuration"""
        return {
            "profile": recommend.get("profile"),
            "priority": recommend.get("priority"),
            "match": recommend.get("match", [])
        }
    
    def get_clock_type(self, config: Dict[str, Any]) -> str:
        """Extract clock type from PTP configuration"""
        for profile in config.get("spec", {}).get("profile", []):
            ptp4l_conf = profile.get("ptp4lConf", {})
            clock_type = ptp4l_conf.get("clock", {}).get("clock_type")
            if clock_type:
                return clock_type
        return "Unknown"
    
    def get_domain_number(self, config: Dict[str, Any]) -> Optional[int]:
        """Extract domain number from PTP configuration"""
        for profile in config.get("spec", {}).get("profile", []):
            ptp4l_conf = profile.get("ptp4lConf", {})
            domain = ptp4l_conf.get("global", {}).get("domainNumber")
            if domain is not None:
                return domain
        return None
    
    def get_priorities(self, config: Dict[str, Any]) -> Dict[str, int]:
        """Extract priority values from PTP configuration"""
        priorities = {}
        for profile in config.get("spec", {}).get("profile", []):
            ptp4l_conf = profile.get("ptp4lConf", {})
            global_conf = ptp4l_conf.get("global", {})
            
            if "priority1" in global_conf:
                priorities["priority1"] = global_conf["priority1"]
            if "priority2" in global_conf:
                priorities["priority2"] = global_conf["priority2"]
        
        return priorities
    
    def get_clock_class(self, config: Dict[str, Any]) -> Optional[int]:
        """Extract clock class from PTP configuration"""
        for profile in config.get("spec", {}).get("profile", []):
            ptp4l_conf = profile.get("ptp4lConf", {})
            clock_class = ptp4l_conf.get("global", {}).get("clockClass")
            if clock_class is not None:
                return clock_class
        return None
    
    def get_sync_intervals(self, config: Dict[str, Any]) -> Dict[str, int]:
        """Extract sync intervals from PTP configuration"""
        intervals = {}
        for profile in config.get("spec", {}).get("profile", []):
            ptp4l_conf = profile.get("ptp4lConf", {})
            global_conf = ptp4l_conf.get("global", {})
            
            if "logSyncInterval" in global_conf:
                intervals["logSyncInterval"] = global_conf["logSyncInterval"]
            if "logAnnounceInterval" in global_conf:
                intervals["logAnnounceInterval"] = global_conf["logAnnounceInterval"]
            if "logMinDelayReqInterval" in global_conf:
                intervals["logMinDelayReqInterval"] = global_conf["logMinDelayReqInterval"]
        
        return intervals
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate PTP configuration and return validation results"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Check for required fields
        if not config.get("spec", {}).get("profile"):
            validation_result["valid"] = False
            validation_result["errors"].append("No profiles defined")
        
        # Check domain number for ITU-T G.8275.1 compliance
        domain = self.get_domain_number(config)
        if domain is not None and (domain < 24 or domain > 43):
            validation_result["warnings"].append(
                f"Domain number {domain} is outside ITU-T G.8275.1 range (24-43)"
            )
        
        # Check clock class
        clock_class = self.get_clock_class(config)
        if clock_class is not None and clock_class > 255:
            validation_result["errors"].append("Invalid clock class (must be 0-255)")
        
        # Check priorities
        priorities = self.get_priorities(config)
        for priority_name, priority_value in priorities.items():
            if priority_value < 0 or priority_value > 255:
                validation_result["errors"].append(
                    f"Invalid {priority_name} value {priority_value} (must be 0-255)"
                )
        
        return validation_result 