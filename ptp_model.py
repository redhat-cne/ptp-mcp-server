#!/usr/bin/env python3
"""
PTP Model - Contextual model layer for PTP understanding and analysis
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ClockType(Enum):
    """PTP Clock Types"""
    ORDINARY_CLOCK = "OC"
    BOUNDARY_CLOCK = "BC"
    TRANSPARENT_CLOCK = "TC"
    GRANDMASTER = "GM"

class BMCARole(Enum):
    """BMCA (Best Master Clock Algorithm) Roles"""
    MASTER = "master"
    SLAVE = "slave"
    PASSIVE = "passive"
    UNKNOWN = "unknown"

class SyncStatus(Enum):
    """PTP Synchronization Status"""
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    HOLDOVER = "holdover"
    FREERUN = "freerun"
    UNKNOWN = "unknown"

@dataclass
class PTPClock:
    """PTP Clock representation"""
    clock_id: str
    clock_type: ClockType
    domain: int
    priority1: int
    priority2: int
    clock_class: int
    clock_accuracy: int
    offset_scaled_log_variance: int
    port_identity: Optional[str] = None
    sync_status: SyncStatus = SyncStatus.UNKNOWN
    bmca_role: BMCARole = BMCARole.UNKNOWN
    last_seen: Optional[datetime] = None

@dataclass
class PTPInterface:
    """PTP Interface representation"""
    name: str
    master_only: bool
    port_state: str
    sync_status: SyncStatus
    offset: Optional[int] = None
    frequency: Optional[int] = None
    last_update: Optional[datetime] = None

@dataclass
class PTPConfiguration:
    """PTP Configuration representation"""
    name: str
    namespace: str
    profiles: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    clock_type: ClockType
    domain: int
    priorities: Dict[str, int]
    clock_class: int
    sync_intervals: Dict[str, int]
    thresholds: Dict[str, Any]

class PTPModel:
    """Contextual model for PTP understanding and analysis"""
    
    def __init__(self):
        # ITU-T G.8275.1 profile knowledge
        self.itu_t_domains = list(range(24, 44))  # Domains 24-43
        self.clock_class_fallback = {
            6: 7,    # Class 6 -> 7
            7: 8,    # Class 7 -> 8
            8: 9,    # Class 8 -> 9
            9: 10,   # Class 9 -> 10
            10: 11,  # Class 10 -> 11
            11: 12,  # Class 11 -> 12
            12: 13,  # Class 12 -> 13
            13: 14,  # Class 13 -> 14
            14: 15,  # Class 14 -> 15
            15: 16,  # Class 15 -> 16
            16: 17,  # Class 16 -> 17
            17: 18,  # Class 17 -> 18
            18: 19,  # Class 18 -> 19
            19: 20,  # Class 19 -> 20
            20: 21,  # Class 20 -> 21
            21: 22,  # Class 21 -> 22
            22: 23,  # Class 22 -> 23
            23: 24,  # Class 23 -> 24
            24: 25,  # Class 24 -> 25
            25: 26,  # Class 25 -> 26
            26: 27,  # Class 26 -> 27
            27: 28,  # Class 27 -> 28
            28: 29,  # Class 28 -> 29
            29: 30,  # Class 29 -> 30
            30: 31,  # Class 30 -> 31
            31: 32,  # Class 31 -> 32
            32: 33,  # Class 32 -> 33
            33: 34,  # Class 33 -> 34
            34: 35,  # Class 34 -> 35
            35: 36,  # Class 35 -> 36
            36: 37,  # Class 36 -> 37
            37: 38,  # Class 37 -> 38
            38: 39,  # Class 38 -> 39
            39: 40,  # Class 39 -> 40
            40: 41,  # Class 40 -> 41
            41: 42,  # Class 41 -> 42
            42: 43,  # Class 42 -> 43
            43: 44,  # Class 43 -> 44
            44: 45,  # Class 44 -> 45
            45: 46,  # Class 45 -> 46
            46: 47,  # Class 46 -> 47
            47: 48,  # Class 47 -> 48
            48: 49,  # Class 48 -> 49
            49: 50,  # Class 49 -> 50
            50: 51,  # Class 50 -> 51
            51: 52,  # Class 51 -> 52
            52: 53,  # Class 52 -> 53
            53: 54,  # Class 53 -> 54
            54: 55,  # Class 54 -> 55
            55: 56,  # Class 55 -> 56
            56: 57,  # Class 56 -> 57
            57: 58,  # Class 57 -> 58
            58: 59,  # Class 58 -> 59
            59: 60,  # Class 59 -> 60
            60: 61,  # Class 60 -> 61
            61: 62,  # Class 61 -> 62
            62: 63,  # Class 62 -> 63
            63: 64,  # Class 63 -> 64
            64: 65,  # Class 64 -> 65
            65: 66,  # Class 65 -> 66
            66: 67,  # Class 66 -> 67
            67: 68,  # Class 67 -> 68
            68: 69,  # Class 68 -> 69
            69: 70,  # Class 69 -> 70
            70: 71,  # Class 70 -> 71
            71: 72,  # Class 71 -> 72
            72: 73,  # Class 72 -> 73
            73: 74,  # Class 73 -> 74
            74: 75,  # Class 74 -> 75
            75: 76,  # Class 75 -> 76
            76: 77,  # Class 76 -> 77
            77: 78,  # Class 77 -> 78
            78: 79,  # Class 78 -> 79
            79: 80,  # Class 79 -> 80
            80: 81,  # Class 80 -> 81
            81: 82,  # Class 81 -> 82
            82: 83,  # Class 82 -> 83
            83: 84,  # Class 83 -> 84
            84: 85,  # Class 84 -> 85
            85: 86,  # Class 85 -> 86
            86: 87,  # Class 86 -> 87
            87: 88,  # Class 87 -> 88
            88: 89,  # Class 88 -> 89
            89: 90,  # Class 89 -> 90
            90: 91,  # Class 90 -> 91
            91: 92,  # Class 91 -> 92
            92: 93,  # Class 92 -> 93
            93: 94,  # Class 93 -> 94
            94: 95,  # Class 94 -> 95
            95: 96,  # Class 95 -> 96
            96: 97,  # Class 96 -> 97
            97: 98,  # Class 97 -> 98
            98: 99,  # Class 98 -> 99
            99: 100, # Class 99 -> 100
            100: 101, # Class 100 -> 101
            101: 102, # Class 101 -> 102
            102: 103, # Class 102 -> 103
            103: 104, # Class 103 -> 104
            104: 105, # Class 104 -> 105
            105: 106, # Class 105 -> 106
            106: 107, # Class 106 -> 107
            107: 108, # Class 107 -> 108
            108: 109, # Class 108 -> 109
            109: 110, # Class 109 -> 110
            110: 111, # Class 110 -> 111
            111: 112, # Class 111 -> 112
            112: 113, # Class 112 -> 113
            113: 114, # Class 113 -> 114
            114: 115, # Class 114 -> 115
            115: 116, # Class 115 -> 116
            116: 117, # Class 116 -> 117
            117: 118, # Class 117 -> 118
            118: 119, # Class 118 -> 119
            119: 120, # Class 119 -> 120
            120: 121, # Class 120 -> 121
            121: 122, # Class 121 -> 122
            122: 123, # Class 122 -> 123
            123: 124, # Class 123 -> 124
            124: 125, # Class 124 -> 125
            125: 126, # Class 125 -> 126
            126: 127, # Class 126 -> 127
            127: 128, # Class 127 -> 128
            128: 129, # Class 128 -> 129
            129: 130, # Class 129 -> 130
            130: 131, # Class 130 -> 131
            131: 132, # Class 131 -> 132
            132: 133, # Class 132 -> 133
            133: 134, # Class 133 -> 134
            134: 135, # Class 134 -> 135
            135: 136, # Class 135 -> 136
            136: 137, # Class 136 -> 137
            137: 138, # Class 137 -> 138
            138: 139, # Class 138 -> 139
            139: 140, # Class 139 -> 140
            140: 141, # Class 140 -> 141
            141: 142, # Class 141 -> 142
            142: 143, # Class 142 -> 143
            143: 144, # Class 143 -> 144
            144: 145, # Class 144 -> 145
            145: 146, # Class 145 -> 146
            146: 147, # Class 146 -> 147
            147: 148, # Class 147 -> 148
            148: 149, # Class 148 -> 149
            149: 150, # Class 149 -> 150
            150: 151, # Class 150 -> 151
            151: 152, # Class 151 -> 152
            152: 153, # Class 152 -> 153
            153: 154, # Class 153 -> 154
            154: 155, # Class 154 -> 155
            155: 156, # Class 155 -> 156
            156: 157, # Class 156 -> 157
            157: 158, # Class 157 -> 158
            158: 159, # Class 158 -> 159
            159: 160, # Class 159 -> 160
            160: 161, # Class 160 -> 161
            161: 162, # Class 161 -> 162
            162: 163, # Class 162 -> 163
            163: 164, # Class 163 -> 164
            164: 165, # Class 164 -> 165
            165: 166, # Class 165 -> 166
            166: 167, # Class 166 -> 167
            167: 168, # Class 167 -> 168
            168: 169, # Class 168 -> 169
            169: 170, # Class 169 -> 170
            170: 171, # Class 170 -> 171
            171: 172, # Class 171 -> 172
            172: 173, # Class 172 -> 173
            173: 174, # Class 173 -> 174
            174: 175, # Class 174 -> 175
            175: 176, # Class 175 -> 176
            176: 177, # Class 176 -> 177
            177: 178, # Class 177 -> 178
            178: 179, # Class 178 -> 179
            179: 180, # Class 179 -> 180
            180: 181, # Class 180 -> 181
            181: 182, # Class 181 -> 182
            182: 183, # Class 182 -> 183
            183: 184, # Class 183 -> 184
            184: 185, # Class 184 -> 185
            185: 186, # Class 185 -> 186
            186: 187, # Class 186 -> 187
            187: 188, # Class 187 -> 188
            188: 189, # Class 188 -> 189
            189: 190, # Class 189 -> 190
            190: 191, # Class 190 -> 191
            191: 192, # Class 191 -> 192
            192: 193, # Class 192 -> 193
            193: 194, # Class 193 -> 194
            194: 195, # Class 194 -> 195
            195: 196, # Class 195 -> 196
            196: 197, # Class 196 -> 197
            197: 198, # Class 197 -> 198
            198: 199, # Class 198 -> 199
            199: 200, # Class 199 -> 200
            200: 201, # Class 200 -> 201
            201: 202, # Class 201 -> 202
            202: 203, # Class 202 -> 203
            203: 204, # Class 203 -> 204
            204: 205, # Class 204 -> 205
            205: 206, # Class 205 -> 206
            206: 207, # Class 206 -> 207
            207: 208, # Class 207 -> 208
            208: 209, # Class 208 -> 209
            209: 210, # Class 209 -> 210
            210: 211, # Class 210 -> 211
            211: 212, # Class 211 -> 212
            212: 213, # Class 212 -> 213
            213: 214, # Class 213 -> 214
            214: 215, # Class 214 -> 215
            215: 216, # Class 215 -> 216
            216: 217, # Class 216 -> 217
            217: 218, # Class 217 -> 218
            218: 219, # Class 218 -> 219
            219: 220, # Class 219 -> 220
            220: 221, # Class 220 -> 221
            221: 222, # Class 221 -> 222
            222: 223, # Class 222 -> 223
            223: 224, # Class 223 -> 224
            224: 225, # Class 224 -> 225
            225: 226, # Class 225 -> 226
            226: 227, # Class 226 -> 227
            227: 228, # Class 227 -> 228
            228: 229, # Class 228 -> 229
            229: 230, # Class 229 -> 230
            230: 231, # Class 230 -> 231
            231: 232, # Class 231 -> 232
            232: 233, # Class 232 -> 233
            233: 234, # Class 233 -> 234
            234: 235, # Class 234 -> 235
            235: 236, # Class 235 -> 236
            236: 237, # Class 236 -> 237
            237: 238, # Class 237 -> 238
            238: 239, # Class 238 -> 239
            239: 240, # Class 239 -> 240
            240: 241, # Class 240 -> 241
            241: 242, # Class 241 -> 242
            242: 243, # Class 242 -> 243
            243: 244, # Class 243 -> 244
            244: 245, # Class 244 -> 245
            245: 246, # Class 245 -> 246
            246: 247, # Class 246 -> 247
            247: 248, # Class 247 -> 248
            248: 249, # Class 248 -> 249
            249: 250, # Class 249 -> 250
            250: 251, # Class 250 -> 251
            251: 252, # Class 251 -> 252
            252: 253, # Class 252 -> 253
            253: 254, # Class 253 -> 254
            254: 255, # Class 254 -> 255
        }
    
    def create_ptp_configuration(self, config_data: Dict[str, Any]) -> PTPConfiguration:
        """Create PTPConfiguration from parsed config data"""
        if not config_data.get("items"):
            raise ValueError("No PTP configuration items found")
        
        # Use first item for now (could be extended to handle multiple configs)
        item = config_data["items"][0]
        
        # Extract basic information
        name = item.get("metadata", {}).get("name", "unknown")
        namespace = item.get("metadata", {}).get("namespace", "openshift-ptp")
        
        # Extract profiles and recommendations
        spec = item.get("spec", {})
        profiles = spec.get("profile", [])
        recommendations = spec.get("recommend", [])
        
        # Determine clock type
        clock_type = self._determine_clock_type(profiles)
        
        # Extract domain
        domain = self._extract_domain(profiles)
        
        # Extract priorities
        priorities = self._extract_priorities(profiles)
        
        # Extract clock class
        clock_class = self._extract_clock_class(profiles)
        
        # Extract sync intervals
        sync_intervals = self._extract_sync_intervals(profiles)
        
        # Extract thresholds
        thresholds = self._extract_thresholds(profiles)
        
        return PTPConfiguration(
            name=name,
            namespace=namespace,
            profiles=profiles,
            recommendations=recommendations,
            clock_type=clock_type,
            domain=domain,
            priorities=priorities,
            clock_class=clock_class,
            sync_intervals=sync_intervals,
            thresholds=thresholds
        )
    
    def _determine_clock_type(self, profiles: List[Dict[str, Any]]) -> ClockType:
        """Determine clock type from profiles"""
        for profile in profiles:
            ptp4l_conf = profile.get("ptp4lConf", {})
            clock_conf = ptp4l_conf.get("clock", {})
            clock_type_str = clock_conf.get("clock_type", "").upper()
            
            if clock_type_str == "BC":
                return ClockType.BOUNDARY_CLOCK
            elif clock_type_str == "TC":
                return ClockType.TRANSPARENT_CLOCK
            elif clock_type_str == "GM":
                return ClockType.GRANDMASTER
            elif clock_type_str == "OC":
                return ClockType.ORDINARY_CLOCK
        
        # Default to Ordinary Clock
        return ClockType.ORDINARY_CLOCK
    
    def _extract_domain(self, profiles: List[Dict[str, Any]]) -> int:
        """Extract domain number from profiles"""
        for profile in profiles:
            ptp4l_conf = profile.get("ptp4lConf", {})
            global_conf = ptp4l_conf.get("global", {})
            domain = global_conf.get("domainNumber")
            if domain is not None:
                return domain
        
        return 0  # Default domain
    
    def _extract_priorities(self, profiles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract priority values from profiles"""
        priorities = {}
        for profile in profiles:
            ptp4l_conf = profile.get("ptp4lConf", {})
            global_conf = ptp4l_conf.get("global", {})
            
            if "priority1" in global_conf:
                priorities["priority1"] = global_conf["priority1"]
            if "priority2" in global_conf:
                priorities["priority2"] = global_conf["priority2"]
        
        return priorities
    
    def _extract_clock_class(self, profiles: List[Dict[str, Any]]) -> int:
        """Extract clock class from profiles"""
        for profile in profiles:
            ptp4l_conf = profile.get("ptp4lConf", {})
            global_conf = ptp4l_conf.get("global", {})
            clock_class = global_conf.get("clockClass")
            if clock_class is not None:
                return clock_class
        
        return 248  # Default clock class
    
    def _extract_sync_intervals(self, profiles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract sync intervals from profiles"""
        intervals = {}
        for profile in profiles:
            ptp4l_conf = profile.get("ptp4lConf", {})
            global_conf = ptp4l_conf.get("global", {})
            
            if "logSyncInterval" in global_conf:
                intervals["logSyncInterval"] = global_conf["logSyncInterval"]
            if "logAnnounceInterval" in global_conf:
                intervals["logAnnounceInterval"] = global_conf["logAnnounceInterval"]
            if "logMinDelayReqInterval" in global_conf:
                intervals["logMinDelayReqInterval"] = global_conf["logMinDelayReqInterval"]
        
        return intervals
    
    def _extract_thresholds(self, profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract clock thresholds from profiles"""
        thresholds = {}
        for profile in profiles:
            ptp_threshold = profile.get("ptpClockThreshold", {})
            if ptp_threshold:
                thresholds.update(ptp_threshold)
        
        return thresholds
    
    def analyze_bmca_state(self, config: PTPConfiguration, logs: List[Any]) -> BMCARole:
        """Analyze BMCA state based on configuration and logs"""
        # This is a simplified analysis - in practice, you'd need more sophisticated logic
        # to determine the actual BMCA state from logs
        
        # Check if this is configured as a grandmaster
        if config.clock_type == ClockType.GRANDMASTER:
            return BMCARole.MASTER
        
        # Check if this is a boundary clock
        if config.clock_type == ClockType.BOUNDARY_CLOCK:
            # Boundary clocks can be master or slave depending on topology
            # For now, assume slave (could be enhanced with log analysis)
            return BMCARole.SLAVE
        
        # Ordinary clocks are typically slaves
        return BMCARole.SLAVE
    
    def analyze_sync_status(self, config: PTPConfiguration, logs: List[Any]) -> SyncStatus:
        """Analyze synchronization status based on configuration and logs"""
        # This would need to be enhanced with actual log analysis
        # For now, return a default status
        
        # Check if free running is enabled
        for profile in config.profiles:
            ptp4l_conf = profile.get("ptp4lConf", {})
            global_conf = ptp4l_conf.get("global", {})
            if global_conf.get("free_running", 0) == 1:
                return SyncStatus.FREERUN
        
        # Default to unknown (would be determined from logs)
        return SyncStatus.UNKNOWN
    
    def validate_itu_t_compliance(self, config: PTPConfiguration) -> Dict[str, Any]:
        """Validate ITU-T G.8275.1 compliance"""
        validation = {
            "compliant": True,
            "warnings": [],
            "errors": []
        }
        
        # Check domain number
        if config.domain not in self.itu_t_domains:
            validation["compliant"] = False
            validation["errors"].append(
                f"Domain {config.domain} is not in ITU-T G.8275.1 range (24-43)"
            )
        
        # Check clock class
        if config.clock_class < 6 or config.clock_class > 255:
            validation["warnings"].append(
                f"Clock class {config.clock_class} is outside recommended range (6-255)"
            )
        
        # Check priorities
        for priority_name, priority_value in config.priorities.items():
            if priority_value < 0 or priority_value > 255:
                validation["errors"].append(
                    f"Invalid {priority_name} value {priority_value} (must be 0-255)"
                )
        
        return validation
    
    def get_clock_class_fallback(self, current_class: int) -> int:
        """Get the fallback clock class according to ITU-T G.8275.1"""
        return self.clock_class_fallback.get(current_class, current_class)
    
    def analyze_timing_traceability(self, config: PTPConfiguration, logs: List[Any]) -> Dict[str, Any]:
        """Analyze timing traceability"""
        traceability = {
            "source": "unknown",
            "quality": "unknown",
            "last_update": None,
            "status": "unknown"
        }
        
        # This would be enhanced with actual log analysis
        # For now, return basic information
        
        return traceability
    
    def detect_sync_loss(self, logs: List[Any]) -> List[Dict[str, Any]]:
        """Detect synchronization loss events from logs"""
        sync_loss_events = []
        
        # This would analyze logs for sync loss indicators
        # For now, return empty list
        
        return sync_loss_events
    
    def get_offset_trend(self, logs: List[Any], time_range: str = "last_hour") -> Dict[str, Any]:
        """Get offset trend analysis"""
        trend = {
            "current_offset": None,
            "trend": "stable",
            "min_offset": None,
            "max_offset": None,
            "average_offset": None,
            "samples": 0
        }
        
        # This would analyze offset data from logs
        # For now, return basic structure
        
        return trend
    
    def get_clock_hierarchy(self, config: PTPConfiguration, logs: List[Any]) -> Dict[str, Any]:
        """Get current clock hierarchy"""
        hierarchy = {
            "grandmaster": None,
            "boundary_clocks": [],
            "ordinary_clocks": [],
            "transparent_clocks": [],
            "current_clock": {
                "type": config.clock_type.value,
                "domain": config.domain,
                "priorities": config.priorities,
                "clock_class": config.clock_class
            }
        }
        
        return hierarchy 