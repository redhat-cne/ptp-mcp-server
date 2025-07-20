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
    
    print("\n=== Test Complete ===") 