#!/usr/bin/env python3
"""
Quick Test Script for PTP MCP Server API
Run this to verify all components are working before building your agent.
"""

import asyncio
import json
import sys
from ptp_tools import PTPTools

async def quick_test():
    """Run a quick test of all API endpoints"""
    print("🔍 PTP MCP Server API Quick Test")
    print("=" * 50)
    
    tools = PTPTools()
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Configuration API
    print("\n1️⃣ Testing Configuration API...")
    total_tests += 1
    try:
        result = await tools.get_ptp_config({"namespace": "openshift-ptp"})
        if result["success"]:
            print("✅ Configuration API: PASSED")
            config = result["configuration"]
            print(f"   - Name: {config.get('name', 'N/A')}")
            print(f"   - Clock Type: {config.get('clock_type', 'N/A')}")
            print(f"   - Domain: {config.get('domain', 'N/A')}")
            tests_passed += 1
        else:
            print(f"❌ Configuration API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Configuration API: FAILED - {str(e)}")
    
    # Test 2: Logs API
    print("\n2️⃣ Testing Logs API...")
    total_tests += 1
    try:
        result = await tools.get_ptp_logs({"lines": 100})
        if result["success"]:
            print("✅ Logs API: PASSED")
            print(f"   - Logs Count: {result.get('logs_count', 0)}")
            print(f"   - Grandmaster: {result.get('grandmaster', {}).get('status', 'unknown')}")
            tests_passed += 1
        else:
            print(f"❌ Logs API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Logs API: FAILED - {str(e)}")
    
    # Test 3: Search API
    print("\n3️⃣ Testing Search API...")
    total_tests += 1
    try:
        result = await tools.search_logs({"query": "dpll"})
        if result["success"]:
            print("✅ Search API: PASSED")
            print(f"   - Total Logs: {result.get('total_logs', 0)}")
            print(f"   - Matching Logs: {result.get('matching_logs', 0)}")
            tests_passed += 1
        else:
            print(f"❌ Search API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Search API: FAILED - {str(e)}")
    
    # Test 4: Health API
    print("\n4️⃣ Testing Health API...")
    total_tests += 1
    try:
        result = await tools.check_ptp_health({})
        if result["success"]:
            print("✅ Health API: PASSED")
            print(f"   - Overall Status: {result.get('overall_status', 'unknown')}")
            tests_passed += 1
        else:
            print(f"❌ Health API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Health API: FAILED - {str(e)}")
    
    # Test 5: Natural Language API
    print("\n5️⃣ Testing Natural Language API...")
    total_tests += 1
    try:
        result = await tools.query_ptp({"question": "What is the current grandmaster?"})
        if result["success"]:
            print("✅ Natural Language API: PASSED")
            print(f"   - Response: {result.get('response', '')[:100]}...")
            tests_passed += 1
        else:
            print(f"❌ Natural Language API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Natural Language API: FAILED - {str(e)}")
    
    # Test 6: Grandmaster Status API
    print("\n6️⃣ Testing Grandmaster Status API...")
    total_tests += 1
    try:
        result = await tools.get_grandmaster_status({})
        if result["success"]:
            print("✅ Grandmaster Status API: PASSED")
            gm_info = result.get("grandmaster", {})
            print(f"   - Status: {gm_info.get('status', 'unknown')}")
            print(f"   - Interface: {gm_info.get('interface', 'unknown')}")
            tests_passed += 1
        else:
            print(f"❌ Grandmaster Status API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Grandmaster Status API: FAILED - {str(e)}")
    
    # Test 7: Sync Status API
    print("\n7️⃣ Testing Sync Status API...")
    total_tests += 1
    try:
        result = await tools.analyze_sync_status({})
        if result["success"]:
            print("✅ Sync Status API: PASSED")
            sync_status = result.get("sync_status", {})
            print(f"   - DPLL Locked: {sync_status.get('dpll_locked', False)}")
            print(f"   - Offset in Range: {sync_status.get('offset_in_range', False)}")
            tests_passed += 1
        else:
            print(f"❌ Sync Status API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Sync Status API: FAILED - {str(e)}")
    
    # Test 8: Clock Hierarchy API
    print("\n8️⃣ Testing Clock Hierarchy API...")
    total_tests += 1
    try:
        result = await tools.get_clock_hierarchy({})
        if result["success"]:
            print("✅ Clock Hierarchy API: PASSED")
            current_clock = result.get("current_clock", {})
            print(f"   - Clock Type: {current_clock.get('type', 'unknown')}")
            print(f"   - Domain: {current_clock.get('domain', 'unknown')}")
            print(f"   - Summary: {result.get('summary', 'N/A')[:80]}")
            tests_passed += 1
        else:
            print(f"❌ Clock Hierarchy API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Clock Hierarchy API: FAILED - {str(e)}")
    
    # Test 9: PMC Query API
    print("\n9️⃣  Testing PMC Query API...")
    total_tests += 1
    try:
        result = await tools.run_pmc_query({"command": "CURRENT_DATA_SET"})
        if result["success"]:
            print("✅ PMC Query API: PASSED")
            print(f"   - Command: {result.get('command', 'N/A')}")
            data = result.get("data", {})
            print(f"   - Steps Removed: {data.get('steps_removed', 'N/A')}")
            tests_passed += 1
        else:
            print(f"❌ PMC Query API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ PMC Query API: FAILED - {str(e)}")

    # Test 10: Servo Stability API
    print("\n🔟 Testing Servo Stability API...")
    total_tests += 1
    try:
        result = await tools.analyze_servo_stability({})
        if result["success"]:
            print("✅ Servo Stability API: PASSED")
            print(f"   - Stability: {result.get('stability', 'unknown')}")
            print(f"   - Servo State: {result.get('servo_state', 'unknown')}")
            tests_passed += 1
        else:
            print(f"❌ Servo Stability API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Servo Stability API: FAILED - {str(e)}")

    # Test 11: Port Status API
    print("\n1️⃣1️⃣ Testing Port Status API...")
    total_tests += 1
    try:
        result = await tools.get_port_status({})
        if result["success"]:
            print("✅ Port Status API: PASSED")
            print(f"   - Current Port State: {result.get('current_port_state', 'N/A')}")
            print(f"   - Ports: {len(result.get('ports', {}))}")
            tests_passed += 1
        else:
            print(f"❌ Port Status API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Port Status API: FAILED - {str(e)}")

    # Test 12: GNSS Status API
    print("\n1️⃣2️⃣ Testing GNSS Status API...")
    total_tests += 1
    try:
        result = await tools.get_gnss_status({})
        if result["success"]:
            print("✅ GNSS Status API: PASSED")
            print(f"   - Fix Status: {result.get('fix_status', 'N/A')}")
            print(f"   - Satellites: {result.get('satellites_used', 'N/A')}")
            tests_passed += 1
        else:
            print(f"❌ GNSS Status API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ GNSS Status API: FAILED - {str(e)}")

    # Test 13: Holdover Analysis API
    print("\n1️⃣3️⃣ Testing Holdover Analysis API...")
    total_tests += 1
    try:
        result = await tools.analyze_holdover({})
        if result["success"]:
            print("✅ Holdover Analysis API: PASSED")
            print(f"   - In Holdover: {result.get('in_holdover', False)}")
            print(f"   - Holdover Events: {len(result.get('holdover_events', []))}")
            tests_passed += 1
        else:
            print(f"❌ Holdover Analysis API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Holdover Analysis API: FAILED - {str(e)}")

    # Test 14: Frequency Drift API
    print("\n1️⃣4️⃣ Testing Frequency Drift API...")
    total_tests += 1
    try:
        result = await tools.analyze_frequency_drift({})
        if result["success"]:
            print("✅ Frequency Drift API: PASSED")
            print(f"   - Trend: {result.get('trend', 'unknown')}")
            print(f"   - Estimated Stability: {result.get('estimated_stability', 'unknown')}")
            tests_passed += 1
        else:
            print(f"❌ Frequency Drift API: FAILED - {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Frequency Drift API: FAILED - {str(e)}")

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! Your API is ready for agent integration.")
        print("\n📋 Available API Endpoints for Agent Integration:")
        print("   • get_ptp_config() - Get PTP configuration")
        print("   • get_ptp_logs() - Get linuxptp daemon logs")
        print("   • search_logs() - Search logs for patterns")
        print("   • get_grandmaster_status() - Get grandmaster info")
        print("   • analyze_sync_status() - Analyze sync status")
        print("   • get_clock_hierarchy() - Get clock hierarchy")
        print("   • check_ptp_health() - Comprehensive health check")
        print("   • query_ptp() - Natural language interface")
        print("   • run_pmc_query() - PMC management queries")
        print("   • analyze_servo_stability() - Servo controller analysis")
        print("   • get_port_status() - Port state and transitions")
        print("   • get_gnss_status() - GNSS receiver status")
        print("   • analyze_holdover() - Holdover event analysis")
        print("   • analyze_frequency_drift() - Frequency drift analysis")
        
        print("\n🔧 Next Steps:")
        print("   1. Start the MCP server: python ptp_mcp_server.py")
        print("   2. Integrate with your agent using the above endpoints")
        print("   3. Use structured JSON responses for agent processing")
        
    elif tests_passed > 0:
        print(f"\n⚠️  PARTIAL SUCCESS: {tests_passed}/{total_tests} tests passed")
        print("   Some APIs are working. Check the failed tests above.")
        
    else:
        print("\n❌ ALL TESTS FAILED!")
        print("   Please check:")
        print("   1. OpenShift cluster access (oc whoami)")
        print("   2. PTP namespace exists (oc get namespace openshift-ptp)")
        print("   3. Dependencies installed (pip install -r requirements.txt)")
        print("   4. Network connectivity to cluster")

def test_sample_data():
    """Test with sample data if cluster is not available"""
    print("\n🧪 Testing with Sample Data (No Cluster Required)")
    print("=" * 50)
    
    # Sample configuration data
    sample_config = {
        "name": "bc-config-1",
        "clock_type": "BC",
        "domain": 24,
        "clock_class": 248,
        "priorities": {"priority1": 128, "priority2": 128}
    }
    
    # Sample log data
    sample_logs = {
        "logs_count": 150,
        "grandmaster": {"status": "s0", "interface": "ens7f0"},
        "sync_status": {"dpll_locked": True, "offset_in_range": True}
    }
    
    print("✅ Sample Configuration:")
    for key, value in sample_config.items():
        print(f"   - {key}: {value}")
    
    print("\n✅ Sample Logs:")
    for key, value in sample_logs.items():
        print(f"   - {key}: {value}")
    
    print("\n📋 API Response Format (for agent integration):")
    print("   All APIs return JSON with 'success' boolean and data/error fields")
    print("   Example: {'success': True, 'configuration': {...}, 'error': None}")

if __name__ == "__main__":
    print("🚀 Starting PTP MCP Server API Quick Test...")
    
    try:
        asyncio.run(quick_test())
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        print("Running sample data test instead...")
        test_sample_data()
    
    print("\n✅ Quick test complete!") 