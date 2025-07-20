#!/usr/bin/env python3
"""
Setup script for PTP MCP Server
"""

import os
import sys
import subprocess
import json

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_dependencies():
    """Install required dependencies"""
    print("\nInstalling dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        sys.exit(1)

def check_openshift_access():
    """Check if OpenShift access is configured"""
    print("\nChecking OpenShift access...")
    try:
        result = subprocess.run(["oc", "whoami"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ OpenShift access configured (user: {result.stdout.strip()})")
            return True
        else:
            print("⚠ OpenShift access not configured")
            print("  Run 'oc login' to configure access")
            return False
    except FileNotFoundError:
        print("⚠ OpenShift CLI (oc) not found")
        print("  Install OpenShift CLI to use this server")
        return False

def check_ptp_namespace():
    """Check if PTP namespace exists"""
    print("\nChecking PTP namespace...")
    try:
        result = subprocess.run(["oc", "get", "namespace", "openshift-ptp"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ openshift-ptp namespace found")
            return True
        else:
            print("⚠ openshift-ptp namespace not found")
            print("  PTP operator may not be installed")
            return False
    except FileNotFoundError:
        print("⚠ OpenShift CLI not available")
        return False

def create_config():
    """Create configuration files"""
    print("\nCreating configuration files...")
    
    # Create .env file for environment variables
    env_content = """# PTP MCP Server Environment Variables
PTP_NAMESPACE=openshift-ptp
PTP_DAEMON_NAME=linuxptp-daemon
PTP_CONTAINER_NAME=linuxptp-daemon-container
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    print("✓ Created .env file")
    
    # Create sample MCP client config
    client_config = {
        "mcpServers": {
            "ptp-mcp-server": {
                "command": "python",
                "args": ["ptp_mcp_server.py"],
                "env": {
                    "PYTHONPATH": ".",
                    "PTP_NAMESPACE": "openshift-ptp",
                    "PTP_DAEMON_NAME": "linuxptp-daemon",
                    "PTP_CONTAINER_NAME": "linuxptp-daemon-container"
                }
            }
        }
    }
    
    with open("mcp_client_config.json", "w") as f:
        json.dump(client_config, f, indent=2)
    print("✓ Created mcp_client_config.json")

def run_tests():
    """Run basic tests"""
    print("\nRunning basic tests...")
    try:
        result = subprocess.run([sys.executable, "test_ptp_server.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Basic tests passed")
        else:
            print("⚠ Tests failed (this is expected without OpenShift cluster)")
            print("  Tests will work when connected to a cluster with PTP")
    except Exception as e:
        print(f"⚠ Test execution failed: {e}")

def show_usage():
    """Show usage instructions"""
    print("\n" + "="*60)
    print("PTP MCP Server Setup Complete!")
    print("="*60)
    
    print("\nUsage:")
    print("1. Start the MCP server:")
    print("   python ptp_mcp_server.py")
    
    print("\n2. Test the server:")
    print("   python test_ptp_server.py")
    
    print("\n3. Run examples:")
    print("   python example_usage.py")
    
    print("\n4. Use with MCP clients:")
    print("   - Configure your MCP client to use mcp_client_config.json")
    print("   - Or use the server directly with MCP-compatible tools")
    
    print("\nAvailable Tools:")
    print("- get_ptp_config: Get PTP configuration")
    print("- get_ptp_logs: Get linuxptp daemon logs")
    print("- search_logs: Search logs for patterns")
    print("- get_grandmaster_status: Get grandmaster info")
    print("- analyze_sync_status: Analyze sync status")
    print("- get_clock_hierarchy: Get clock hierarchy")
    print("- check_ptp_health: Comprehensive health check")
    print("- query_ptp: Natural language interface")
    
    print("\nExample Queries:")
    print("- 'What is the current grandmaster?'")
    print("- 'Show ptpconfig parameters'")
    print("- 'Check for sync loss'")
    print("- 'Search logs for clockClass change'")
    print("- 'Get offset trend in last hour'")
    print("- 'What is the BMCA state?'")
    print("- 'Show current clock hierarchy'")
    print("- 'Check PTP health'")
    print("- 'Validate ITU-T G.8275.1 compliance'")

def main():
    """Main setup function"""
    print("PTP MCP Server Setup")
    print("="*30)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_dependencies()
    
    # Check OpenShift access
    openshift_ok = check_openshift_access()
    
    # Check PTP namespace (if OpenShift is available)
    if openshift_ok:
        check_ptp_namespace()
    
    # Create configuration files
    create_config()
    
    # Run tests
    run_tests()
    
    # Show usage
    show_usage()

if __name__ == "__main__":
    main() 