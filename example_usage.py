#!/usr/bin/env python3
"""
Example usage of PTP MCP Server
"""

import asyncio
import json
from ptp_tools import PTPTools

async def demonstrate_ptp_queries():
    """Demonstrate various PTP queries"""
    tools = PTPTools()
    
    print("=== PTP MCP Server Example Usage ===\n")
    
    # Example 1: Get PTP configuration
    print("1. Getting PTP Configuration")
    print("-" * 40)
    try:
        config_result = await tools.get_ptp_config({"namespace": "openshift-ptp"})
        if config_result["success"]:
            config = config_result["configuration"]
            print(f"✓ Configuration retrieved successfully")
            print(f"  - Name: {config['name']}")
            print(f"  - Clock Type: {config['clock_type']}")
            print(f"  - Domain: {config['domain']}")
            print(f"  - Clock Class: {config['clock_class']}")
            print(f"  - Priorities: {config['priorities']}")
        else:
            print(f"✗ Failed to get configuration: {config_result.get('error')}")
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Natural language queries
    print("2. Natural Language Queries")
    print("-" * 40)
    
    queries = [
        "What is the current grandmaster?",
        "Show ptpconfig parameters",
        "Check for sync loss",
        "What is the BMCA state?",
        "Show current clock hierarchy"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        try:
            result = await tools.query_ptp({"question": query})
            if result["success"]:
                print("Response:")
                print(result["response"])
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Exception: {str(e)}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Log analysis
    print("3. Log Analysis")
    print("-" * 40)
    
    try:
        # Get logs
        logs_result = await tools.get_ptp_logs({
            "namespace": "openshift-ptp",
            "lines": 500
        })
        
        if logs_result["success"]:
            print(f"✓ Retrieved {logs_result['logs_count']} log entries")
            
            # Extract grandmaster info
            gm_info = logs_result["grandmaster"]
            print(f"  - Grandmaster Status: {gm_info.get('status', 'unknown')}")
            print(f"  - Interface: {gm_info.get('interface', 'unknown')}")
            print(f"  - Last Offset: {gm_info.get('offset', 'unknown')} ns")
            
            # Extract sync status
            sync_status = logs_result["sync_status"]
            print(f"  - DPLL Locked: {sync_status.get('dpll_locked', False)}")
            print(f"  - Offset in Range: {sync_status.get('offset_in_range', False)}")
            print(f"  - GNSS Available: {sync_status.get('gnss_available', False)}")
        else:
            print(f"✗ Failed to get logs: {logs_result.get('error')}")
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 4: Health check
    print("4. Comprehensive Health Check")
    print("-" * 40)
    
    try:
        health_result = await tools.check_ptp_health({
            "check_config": True,
            "check_sync": True,
            "check_logs": True
        })
        
        if health_result["success"]:
            print(f"✓ Overall Status: {health_result['overall_status']}")
            
            checks = health_result["checks"]
            for check_name, check_result in checks.items():
                print(f"\n{check_name.title()} Check:")
                if isinstance(check_result, dict):
                    for key, value in check_result.items():
                        print(f"  - {key}: {value}")
                else:
                    print(f"  - Result: {check_result}")
        else:
            print(f"✗ Health check failed: {health_result.get('error')}")
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 5: Log search
    print("5. Log Search Examples")
    print("-" * 40)
    
    search_queries = [
        {"query": "clockClass change", "time_range": "last_hour"},
        {"query": "sync loss", "time_range": "last_day"},
        {"query": "error", "log_level": "error"},
        {"query": "dpll", "time_range": "last_30m"}
    ]
    
    for search_params in search_queries:
        print(f"\nSearching for: '{search_params['query']}'")
        try:
            search_result = await tools.search_logs(search_params)
            
            if search_result["success"]:
                print(f"  ✓ Found {search_result['matching_logs']} matches out of {search_result['total_logs']} logs")
                if search_result["results"]:
                    print("  Sample results:")
                    for i, result in enumerate(search_result["results"][:2]):  # Show first 2
                        print(f"    {i+1}. [{result['timestamp']}] {result['component']}: {result['message'][:80]}...")
            else:
                print(f"  ✗ Search failed: {search_result.get('error')}")
        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 6: Clock hierarchy
    print("6. Clock Hierarchy Analysis")
    print("-" * 40)
    
    try:
        hierarchy_result = await tools.get_clock_hierarchy({
            "include_ports": True,
            "include_priorities": True
        })
        
        if hierarchy_result["success"]:
            hierarchy = hierarchy_result["hierarchy"]
            current_clock = hierarchy.get("current_clock", {})
            
            print(f"✓ Current Clock: {current_clock.get('type', 'unknown')}")
            print(f"  - Domain: {current_clock.get('domain', 'unknown')}")
            print(f"  - Clock Class: {current_clock.get('clock_class', 'unknown')}")
            print(f"  - Priorities: {current_clock.get('priorities', {})}")
            
            grandmaster = hierarchy.get("grandmaster")
            if grandmaster:
                print(f"  - Grandmaster: Active")
            else:
                print(f"  - Grandmaster: Not detected")
            
            if "ports" in hierarchy_result:
                ports = hierarchy_result["ports"]
                print(f"  - Ports: {len(ports)} configured")
                for port in ports:
                    print(f"    * {port['name']}: master_only={port['master_only']}")
        else:
            print(f"✗ Failed to get hierarchy: {hierarchy_result.get('error')}")
    except Exception as e:
        print(f"✗ Exception: {str(e)}")

def show_available_queries():
    """Show available query examples"""
    print("\n=== Available Query Examples ===")
    print("Natural Language Queries:")
    print("  - 'What is the current grandmaster?'")
    print("  - 'Show ptpconfig parameters'")
    print("  - 'Check for sync loss'")
    print("  - 'Search logs for clockClass change'")
    print("  - 'Get offset trend in last hour'")
    print("  - 'What is the BMCA state?'")
    print("  - 'Show current clock hierarchy'")
    print("  - 'Check PTP health'")
    print("  - 'Validate ITU-T G.8275.1 compliance'")
    
    print("\nStructured Queries:")
    print("  - get_ptp_config: Get PTP configuration")
    print("  - get_ptp_logs: Get linuxptp daemon logs")
    print("  - search_logs: Search logs for patterns")
    print("  - get_grandmaster_status: Get grandmaster info")
    print("  - analyze_sync_status: Analyze sync status")
    print("  - get_clock_hierarchy: Get clock hierarchy")
    print("  - check_ptp_health: Comprehensive health check")
    print("  - query_ptp: Natural language interface")

if __name__ == "__main__":
    print("PTP MCP Server - Example Usage")
    print("This example demonstrates the various capabilities of the PTP MCP server.")
    print("Note: Requires an OpenShift cluster with PTP configured.\n")
    
    try:
        asyncio.run(demonstrate_ptp_queries())
    except Exception as e:
        print(f"Example failed: {str(e)}")
        print("This is expected if no OpenShift cluster is available.")
    
    show_available_queries()
    
    print("\n=== Example Complete ===")
    print("To use this MCP server:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Configure OpenShift access (oc login)")
    print("3. Start the MCP server: python ptp_mcp_server.py")
    print("4. Use with MCP-compatible clients") 