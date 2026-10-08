#!/usr/bin/env python3
"""
Test script for PTP MCP Server functionality
"""

import asyncio
import json
import logging
from ptp_tools import PTPTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ptp_tools():
    """Test the PTP tools functionality"""
    tools = PTPTools()
    
    print("=== PTP MCP Server Test ===\n")
    
    # Test 1: Natural language query
    print("1. Testing natural language query:")
    print("Question: 'What is the current grandmaster?'")
    
    try:
        result = await tools.query_ptp({
            "question": "What is the current grandmaster?",
            "context": "Testing PTP server functionality"
        })
        
        if result["success"]:
            print("Response:")
            print(result["response"])
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            if "suggestions" in result:
                print("Suggested queries:")
                for suggestion in result["suggestions"]:
                    print(f"  - {suggestion}")
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Configuration query
    print("2. Testing configuration query:")
    print("Question: 'Show ptpconfig parameters'")
    
    try:
        result = await tools.query_ptp({
            "question": "Show ptpconfig parameters"
        })
        
        if result["success"]:
            print("Response:")
            print(result["response"])
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Sync status query
    print("3. Testing sync status query:")
    print("Question: 'Check for sync loss'")
    
    try:
        result = await tools.query_ptp({
            "question": "Check for sync loss"
        })
        
        if result["success"]:
            print("Response:")
            print(result["response"])
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Health check
    print("4. Testing health check:")
    
    try:
        result = await tools.check_ptp_health({
            "check_config": True,
            "check_sync": True,
            "check_logs": True
        })
        
        if result["success"]:
            print(f"Overall Status: {result['overall_status']}")
            print("Checks:")
            for check_name, check_result in result["checks"].items():
                print(f"  - {check_name}: {check_result}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 5: Log search
    print("5. Testing log search:")
    print("Query: 'clockClass change'")
    
    try:
        result = await tools.search_logs({
            "query": "clockClass change",
            "time_range": "last_hour"
        })
        
        if result["success"]:
            print(f"Found {result['matching_logs']} matching logs out of {result['total_logs']} total")
            if result["results"]:
                print("Sample results:")
                for i, log_entry in enumerate(result["results"][:3]):  # Show first 3
                    print(f"  {i+1}. [{log_entry['timestamp']}] {log_entry['component']}: {log_entry['message']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Exception: {str(e)}")

def demonstrate_sample_data():
    """Demonstrate how the server would work with sample data"""
    print("\n=== Sample Data Demonstration ===\n")
    
    # Sample ptpconfig data (based on the provided example)
    sample_config = {
        "apiVersion": "ptp.openshift.io/v1",
        "kind": "PtpConfigList",
        "items": [{
            "metadata": {
                "name": "bc-config-1",
                "namespace": "openshift-ptp"
            },
            "spec": {
                "profile": [{
                    "name": "profile1",
                    "ptpSchedulingPolicy": "SCHED_FIFO",
                    "ptpSchedulingPriority": 10,
                    "phc2sysOpts": "",
                    "ptp4lConf": """
[ens1f0]
masterOnly 0
[ens1f1]
masterOnly 1
[global]
twoStepFlag 1
priority1 128
priority2 128
domainNumber 24
clockClass 248
clockAccuracy 0xFE
offsetScaledLogVariance 0xFFFF
free_running 0
logAnnounceInterval -3
logSyncInterval -4
logMinDelayReqInterval -4
logMinPdelayReqInterval -4
clock_type BC
network_transport L2
delay_mechanism E2E
""",
                    "ptp4lOpts": "-s -2 --summary_interval -4",
                    "ptpClockThreshold": {
                        "holdOverTimeout": 60,
                        "maxOffsetThreshold": 100,
                        "minOffsetThreshold": -100
                    }
                }],
                "recommend": [{
                    "profile": "profile1",
                    "priority": 4,
                    "match": [{
                        "nodeLabel": "node-role.kubernetes.io/worker"
                    }]
                }]
            }
        }]
    }
    
    # Sample log data (based on the provided example)
    sample_logs = [
        "13:32:21.379479  582727 dpll.go:377] setting phase offset to -2 ns for clock id 5799633565433967748 iface ens7f0",
        "I0720 13:32:21.379506  582727 dpll.go:689] dpll is locked, source is not lost, offset is in range, state is DPLL_LOCKED_HO_ACQ(ens7f0)",
        "I0720 13:32:21.379524  582727 dpll.go:757] dpll event sent for (ens7f0)",
        "I0720 13:32:21.379530  582727 dpll.go:720] ens7f0-dpll decision: Status 3, Offset -2, In spec true, Source GNSS lost false, On holdover false",
        "phc2sys[13465352.526]: [ptp4l.0.config:6] CLOCK_REALTIME phc offset       -12 s2 freq   -6701 delay    565",
        "phc2sys[13465352.589]: [ptp4l.0.config:6] CLOCK_REALTIME phc offset        -9 s2 freq   -6702 delay    571",
        "GM[1753018342]:[ts2phc.0.config] ens7f0 T-GM-STATUS s0",
        "ts2phc[13465353.288]: [ts2phc.0.config:7] nmea sentence: GNRMC,133222.00,A,3553.86858,N,07852.73978,W,0.000,,200725,,,A,V"
    ]
    
    print("Sample PTP Configuration Analysis:")
    print(f"- Clock Type: Boundary Clock (BC)")
    print(f"- Domain: 24 (ITU-T G.8275.1 compliant)")
    print(f"- Priorities: Priority1=128, Priority2=128")
    print(f"- Clock Class: 248")
    print(f"- Sync Intervals: Announce=-3, Sync=-4, DelayReq=-4")
    print(f"- Thresholds: Holdover=60s, Offset=±100ns")
    
    print("\nSample Log Analysis:")
    print("- DPLL Status: LOCKED (Status 3)")
    print("- Offset: -2 ns (in specification)")
    print("- GNSS: Available (not lost)")
    print("- Holdover: False")
    print("- Grandmaster Status: s0 (active)")
    print("- PHC2SYS Offset: -12 to -9 ns")
    print("- NMEA: GPS data available")
    
    print("\nHealth Assessment:")
    print("- Configuration: VALID (ITU-T G.8275.1 compliant)")
    print("- Synchronization: HEALTHY (DPLL locked, offset in range)")
    print("- GNSS: AVAILABLE")
    print("- Overall Status: HEALTHY")

def build_config_data(profiles, name="test-config"):
    """Helper to wrap profiles in a PtpConfigList structure."""
    return {
        "apiVersion": "ptp.openshift.io/v1",
        "kind": "PtpConfigList",
        "items": [{
            "metadata": {"name": name, "namespace": "openshift-ptp"},
            "spec": {
                "profile": profiles,
                "recommend": []
            }
        }]
    }


def test_clock_type_detection():
    """Test clock type detection including T-BC and dual-profile BC"""
    from ptp_model import PTPModel, ClockType

    model = PTPModel()
    passed = 0
    failed = 0

    def check(label, got, expected):
        nonlocal passed, failed
        if got == expected:
            passed += 1
            print(f"  PASS: {label}")
        else:
            failed += 1
            print(f"  FAIL: {label} — expected {expected}, got {got}")

    print("\n=== Clock Type Detection Tests ===\n")

    # --- Single-profile BC (ptp4l_clock_type in [global]) ---
    print("1. Single-profile BC with ptp4l_clock_type in [global]")
    config = build_config_data([{
        "name": "bc-profile",
        "ptp4lConf": {
            "global": {"ptp4l_clock_type": "BC", "domainNumber": 24, "boundary_clock_jbod": 1},
            "interfaces": {"ens1f0": {"masterOnly": 0}, "ens1f1": {"masterOnly": 1}},
            "servo": {}, "transport": {}, "clock": {}
        },
    }])
    ptp_config = model.create_ptp_configuration(config)
    check("clock_type is BC", ptp_config.clock_type, ClockType.BOUNDARY_CLOCK)
    check("no profile_group", ptp_config.profile_group, None)
    check("no receiver_profile", ptp_config.receiver_profile, None)

    # --- T-BC: two profiles with controllingProfile + ts2phc ---
    print("\n2. T-BC: receiver + transmitter with ts2phc")
    config = build_config_data([
        {
            "name": "tbc-tr",
            "phc2sysOpts": "-a -r",
            "ts2phcConf": "[global]\nuse_syslog 0\n[ens1f0]\nts2phc.extts_polarity rising\n",
            "ptp4lConf": {
                "global": {"ptp4l_clock_type": "OC", "domainNumber": 24, "clockClass": 248,
                           "boundary_clock_jbod": 1, "slaveOnly": 0},
                "interfaces": {"ens1f0": {"masterOnly": 0}},
                "servo": {}, "transport": {}, "clock": {}
            },
            "ptpSettings": {},
        },
        {
            "name": "tbc-tt",
            "ptp4lConf": {
                "global": {"ptp4l_clock_type": "BC", "domainNumber": 24, "clockClass": 248,
                           "boundary_clock_jbod": 1},
                "interfaces": {"ens1f1": {"masterOnly": 1}},
                "servo": {}, "transport": {}, "clock": {}
            },
            "ptpSettings": {"controllingProfile": "tbc-tr", "logReduce": "false"},
        },
    ])
    ptp_config = model.create_ptp_configuration(config)
    check("clock_type is T-BC", ptp_config.clock_type, ClockType.TELECOM_BOUNDARY_CLOCK)
    check("receiver_profile is tbc-tr", ptp_config.receiver_profile, "tbc-tr")
    check("transmitter_profile is tbc-tt", ptp_config.transmitter_profile, "tbc-tt")
    check("has_ts2phc is True", ptp_config.has_ts2phc, True)
    check("profile_group exists", ptp_config.profile_group is not None, True)
    check("no warnings", len(ptp_config.warnings), 0)

    # --- Dual-profile BC: controllingProfile but no ts2phc ---
    print("\n3. Dual-profile BC: controllingProfile without ts2phc")
    config = build_config_data([
        {
            "name": "bc-slave",
            "phc2sysOpts": "-a -r",
            "ptp4lConf": {
                "global": {"ptp4l_clock_type": "OC", "domainNumber": 24},
                "interfaces": {"ens2f0": {"masterOnly": 0}},
                "servo": {}, "transport": {}, "clock": {}
            },
            "ptpSettings": {},
        },
        {
            "name": "bc-master",
            "ptp4lConf": {
                "global": {"ptp4l_clock_type": "BC", "domainNumber": 24},
                "interfaces": {"ens2f1": {"masterOnly": 1}},
                "servo": {}, "transport": {}, "clock": {}
            },
            "ptpSettings": {"controllingProfile": "bc-slave"},
        },
    ])
    ptp_config = model.create_ptp_configuration(config)
    check("clock_type is BC", ptp_config.clock_type, ClockType.BOUNDARY_CLOCK)
    check("receiver_profile is bc-slave", ptp_config.receiver_profile, "bc-slave")
    check("transmitter_profile is bc-master", ptp_config.transmitter_profile, "bc-master")
    check("has_ts2phc is False", ptp_config.has_ts2phc, False)
    check("profile_group exists", ptp_config.profile_group is not None, True)

    # --- Invalid controllingProfile reference ---
    print("\n4. Invalid controllingProfile — missing target profile")
    config = build_config_data([
        {
            "name": "orphan",
            "ptp4lConf": {
                "global": {"ptp4l_clock_type": "OC", "domainNumber": 24},
                "interfaces": {"ens3f0": {"masterOnly": 1}},
                "servo": {}, "transport": {}, "clock": {}
            },
            "ptpSettings": {"controllingProfile": "does-not-exist"},
        },
    ])
    ptp_config = model.create_ptp_configuration(config)
    check("clock_type falls back to OC", ptp_config.clock_type, ClockType.ORDINARY_CLOCK)
    check("no profile_group", ptp_config.profile_group, None)
    check("warning emitted", len(ptp_config.warnings) > 0, True)
    check("warning mentions missing profile",
          "does-not-exist" in ptp_config.warnings[0], True)

    # --- Single-profile OC (default) ---
    print("\n5. Single-profile OC (no ptp4l_clock_type set)")
    config = build_config_data([{
        "name": "oc-profile",
        "ptp4lConf": {
            "global": {"domainNumber": 24},
            "interfaces": {"ens4f0": {"masterOnly": 0}},
            "servo": {}, "transport": {}, "clock": {}
        },
    }])
    ptp_config = model.create_ptp_configuration(config)
    check("clock_type defaults to OC", ptp_config.clock_type, ClockType.ORDINARY_CLOCK)

    # --- T-BC with mismatched port roles (warning but still groups) ---
    print("\n6. T-BC with mismatched port roles on controlling profile")
    config = build_config_data([
        {
            "name": "tbc-tr-bad",
            "ts2phcConf": "[global]\nverbose 1\n",
            "ptp4lConf": {
                "global": {"ptp4l_clock_type": "OC", "domainNumber": 24},
                "interfaces": {"ens5f0": {"masterOnly": 1}},
                "servo": {}, "transport": {}, "clock": {}
            },
            "ptpSettings": {},
        },
        {
            "name": "tbc-tt-bad",
            "ptp4lConf": {
                "global": {"ptp4l_clock_type": "BC", "domainNumber": 24},
                "interfaces": {"ens5f1": {"masterOnly": 1}},
                "servo": {}, "transport": {}, "clock": {}
            },
            "ptpSettings": {"controllingProfile": "tbc-tr-bad"},
        },
    ])
    ptp_config = model.create_ptp_configuration(config)
    check("clock_type is still T-BC", ptp_config.clock_type, ClockType.TELECOM_BOUNDARY_CLOCK)
    check("warnings about port role mismatch", len(ptp_config.warnings) > 0, True)

    # --- Self-referencing controllingProfile ---
    print("\n7. Self-referencing controllingProfile")
    config = build_config_data([{
        "name": "self-ref",
        "ptp4lConf": {
            "global": {"ptp4l_clock_type": "BC", "domainNumber": 24},
            "interfaces": {"ens6f0": {"masterOnly": 0}},
            "servo": {}, "transport": {}, "clock": {}
        },
        "ptpSettings": {"controllingProfile": "self-ref"},
    }])
    ptp_config = model.create_ptp_configuration(config)
    check("clock_type falls back to BC", ptp_config.clock_type, ClockType.BOUNDARY_CLOCK)
    check("no profile_group", ptp_config.profile_group, None)
    check("warning about self-reference", len(ptp_config.warnings) > 0, True)

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


def test_config_parser_profile_fields():
    """Test that ptp_config_parser extracts ts2phcConf, ts2phcOpts, and ptpSettings."""
    from ptp_config_parser import PTPConfigParser

    parser = PTPConfigParser()
    passed = 0
    failed = 0

    def check(label, got, expected):
        nonlocal passed, failed
        if got == expected:
            passed += 1
            print(f"  PASS: {label}")
        else:
            failed += 1
            print(f"  FAIL: {label} — expected {expected!r}, got {got!r}")

    print("\n=== Config Parser Profile Field Tests ===\n")

    raw = {
        "apiVersion": "ptp.openshift.io/v1",
        "kind": "PtpConfigList",
        "items": [{
            "metadata": {"name": "tbc"},
            "spec": {
                "profile": [
                    {
                        "name": "tbc-tr",
                        "ptp4lConf": "[global]\nclock_type OC\n",
                        "ts2phcOpts": "-s generic",
                        "ts2phcConf": "[global]\nverbose 1\n",
                        "ptpSettings": {"inSyncConditionThreshold": "10"},
                    },
                    {
                        "name": "tbc-tt",
                        "ptp4lConf": "[global]\nclock_type BC\n",
                        "ptpSettings": {"controllingProfile": "tbc-tr"},
                    },
                ],
                "recommend": []
            }
        }]
    }

    result = parser._parse_ptp_configs(raw)
    profiles = result["items"][0]["spec"]["profile"]

    p0 = profiles[0]
    check("profile 0 name", p0["name"], "tbc-tr")
    check("profile 0 ts2phcOpts", p0["ts2phcOpts"], "-s generic")
    check("profile 0 ts2phcConf non-empty", bool(p0["ts2phcConf"]), True)
    check("profile 0 ptpSettings", p0["ptpSettings"], {"inSyncConditionThreshold": "10"})

    p1 = profiles[1]
    check("profile 1 name", p1["name"], "tbc-tt")
    check("profile 1 ts2phcConf empty", p1.get("ts2phcConf", ""), "")
    check("profile 1 controllingProfile",
          p1["ptpSettings"].get("controllingProfile"), "tbc-tr")

    # Verify parser rename from clock_type -> ptp4l_clock_type
    check("profile 0 ptp4l_clock_type in global",
          p0["ptp4lConf"]["global"].get("ptp4l_clock_type"), "OC")
    check("profile 0 legacy clock_type removed",
          p0["ptp4lConf"]["global"].get("clock_type"), None)

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


if __name__ == "__main__":
    print("PTP MCP Server Test Suite")
    print("Note: This test requires an OpenShift cluster with PTP configured.")
    print("If no cluster is available, the sample data demonstration will show expected behavior.\n")
    
    # Run the test
    try:
        asyncio.run(test_ptp_tools())
    except Exception as e:
        print(f"Test failed: {str(e)}")
        print("\nRunning sample data demonstration instead...")
        demonstrate_sample_data()

    # Always run unit tests for clock type detection
    all_pass = True
    all_pass = test_clock_type_detection() and all_pass
    all_pass = test_config_parser_profile_fields() and all_pass

    if all_pass:
        print("\n=== All Tests Passed ===")
    else:
        print("\n=== Some Tests Failed ===")
        exit(1) 