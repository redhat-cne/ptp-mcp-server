#!/usr/bin/env python3
"""
Performance Test for PTP MCP Server API
"""

import asyncio
import time
from ptp_tools import PTPTools

async def performance_test():
    """Test performance of all API endpoints"""
    print("🚀 PTP MCP Server Performance Test")
    print("=" * 50)
    
    tools = PTPTools()
    
    # Test individual endpoints
    endpoints = [
        ("Configuration API", lambda: tools.get_ptp_config({})),
        ("Logs API", lambda: tools.get_ptp_logs({"lines": 100})),
        ("Health API", lambda: tools.check_ptp_health({})),
        ("Query API", lambda: tools.query_ptp({"question": "What is the current grandmaster?"})),
        ("Search API", lambda: tools.search_logs({"query": "dpll"})),
        ("Grandmaster API", lambda: tools.get_grandmaster_status({})),
        ("Sync Status API", lambda: tools.analyze_sync_status({})),
        ("Clock Hierarchy API", lambda: tools.get_clock_hierarchy({}))
    ]
    
    results = {}
    
    for name, api_call in endpoints:
        print(f"\n⏱️  Testing {name}...")
        start_time = time.time()
        
        try:
            result = await api_call()
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.get("success", False)
            status = "✅ PASS" if success else "❌ FAIL"
            
            print(f"   {status} - {duration:.2f}s")
            results[name] = {
                "success": success,
                "duration": duration,
                "error": result.get("error") if not success else None
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"   ❌ ERROR - {duration:.2f}s - {str(e)}")
            results[name] = {
                "success": False,
                "duration": duration,
                "error": str(e)
            }
    
    # Concurrent performance test
    print(f"\n🔄 Testing Concurrent Operations...")
    start_time = time.time()
    
    try:
        concurrent_results = await asyncio.gather(*[
            tools.get_ptp_config({}),
            tools.get_ptp_logs({"lines": 100}),
            tools.check_ptp_health({}),
            tools.query_ptp({"question": "What is the current grandmaster?"})
        ])
        
        end_time = time.time()
        concurrent_duration = end_time - start_time
        success_count = sum(1 for r in concurrent_results if r.get("success"))
        
        print(f"   Concurrent Test: {success_count}/4 successful in {concurrent_duration:.2f}s")
        results["Concurrent"] = {
            "success": success_count == 4,
            "duration": concurrent_duration,
            "success_count": success_count
        }
        
    except Exception as e:
        end_time = time.time()
        concurrent_duration = end_time - start_time
        print(f"   ❌ Concurrent Test Error: {concurrent_duration:.2f}s - {str(e)}")
        results["Concurrent"] = {
            "success": False,
            "duration": concurrent_duration,
            "error": str(e)
        }
    
    # Summary
    print(f"\n" + "=" * 50)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r["success"])
    total_duration = sum(r["duration"] for r in results.values())
    avg_duration = total_duration / total_tests if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Average Duration: {avg_duration:.2f}s")
    
    # Individual results
    print(f"\n📋 Individual Results:")
    for name, result in results.items():
        status = "✅" if result["success"] else "❌"
        duration = result["duration"]
        print(f"   {status} {name}: {duration:.2f}s")
        if not result["success"] and result.get("error"):
            print(f"      Error: {result['error']}")
    
    # Performance assessment
    print(f"\n🎯 Performance Assessment:")
    if avg_duration < 2.0:
        print("   🟢 EXCELLENT - All APIs responding quickly")
    elif avg_duration < 5.0:
        print("   🟡 GOOD - APIs responding within acceptable range")
    else:
        print("   🔴 SLOW - APIs taking too long to respond")
    
    if successful_tests == total_tests:
        print("   🎉 ALL TESTS PASSED - API is ready for production!")
    else:
        print(f"   ⚠️  {total_tests - successful_tests} tests failed - Check errors above")

if __name__ == "__main__":
    asyncio.run(performance_test()) 