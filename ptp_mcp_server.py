#!/usr/bin/env python3
"""
PTP MCP Server - Model Context Protocol server for OpenShift PTP monitoring
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)

# Import our PTP modules
from ptp_config_parser import PTPConfigParser
from ptp_log_parser import PTPLogParser
from ptp_model import PTPModel
from ptp_query_engine import PTPQueryEngine
from ptp_tools import PTPTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PTPMCPServer:
    """MCP Server for PTP monitoring and analysis"""
    
    def __init__(self):
        self.server = Server("ptp-mcp-server")
        self.ptp_config_parser = PTPConfigParser()
        self.ptp_log_parser = PTPLogParser()
        self.ptp_model = PTPModel()
        self.ptp_query_engine = PTPQueryEngine()
        self.ptp_tools = PTPTools()
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all PTP-related tools with the MCP server"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List all available PTP tools"""
            tools = [
                Tool(
                    name="get_ptp_config",
                    description="Get current PTP configuration from OpenShift cluster",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Namespace containing PTP resources"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_ptp_logs",
                    description="Get linuxptp daemon logs from OpenShift cluster",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Namespace containing PTP daemon"
                            },
                            "lines": {
                                "type": "integer",
                                "default": 1000,
                                "description": "Number of log lines to retrieve"
                            },
                            "since": {
                                "type": "string",
                                "description": "Time since to get logs (e.g., '1h', '30m')"
                            }
                        }
                    }
                ),
                Tool(
                    name="search_logs",
                    description="Search PTP logs for specific patterns or events",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'clockClass change', 'sync loss')"
                            },
                            "time_range": {
                                "type": "string",
                                "description": "Time range for search (e.g., 'last_hour', 'last_day')"
                            },
                            "log_level": {
                                "type": "string",
                                "enum": ["error", "warning", "info", "debug"],
                                "description": "Minimum log level to include"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_grandmaster_status",
                    description="Get current grandmaster clock status and information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "detailed": {
                                "type": "boolean",
                                "default": False,
                                "description": "Include detailed grandmaster information"
                            }
                        }
                    }
                ),
                Tool(
                    name="analyze_sync_status",
                    description="Analyze PTP synchronization status and health",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_offsets": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include offset analysis"
                            },
                            "include_bmca": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include BMCA state analysis"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_clock_hierarchy",
                    description="Get current PTP clock hierarchy and topology",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_ports": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include port information"
                            },
                            "include_priorities": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include priority information"
                            }
                        }
                    }
                ),
                Tool(
                    name="check_ptp_health",
                    description="Comprehensive PTP health check and diagnostics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "check_config": {
                                "type": "boolean",
                                "default": True,
                                "description": "Check configuration validity"
                            },
                            "check_sync": {
                                "type": "boolean",
                                "default": True,
                                "description": "Check synchronization status"
                            },
                            "check_logs": {
                                "type": "boolean",
                                "default": True,
                                "description": "Check for log errors and warnings"
                            }
                        }
                    }
                ),
                Tool(
                    name="query_ptp",
                    description="Natural language query interface for PTP information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Natural language question about PTP (e.g., 'What is the current grandmaster?')"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context for the query"
                            }
                        },
                        "required": ["question"]
                    }
                )
            ]
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls for PTP operations"""
            try:
                if name == "get_ptp_config":
                    result = await self.ptp_tools.get_ptp_config(arguments)
                elif name == "get_ptp_logs":
                    result = await self.ptp_tools.get_ptp_logs(arguments)
                elif name == "search_logs":
                    result = await self.ptp_tools.search_logs(arguments)
                elif name == "get_grandmaster_status":
                    result = await self.ptp_tools.get_grandmaster_status(arguments)
                elif name == "analyze_sync_status":
                    result = await self.ptp_tools.analyze_sync_status(arguments)
                elif name == "get_clock_hierarchy":
                    result = await self.ptp_tools.get_clock_hierarchy(arguments)
                elif name == "check_ptp_health":
                    result = await self.ptp_tools.check_ptp_health(arguments)
                elif name == "query_ptp":
                    result = await self.ptp_tools.query_ptp(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )
                
            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ptp-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

async def main():
    """Main entry point"""
    server = PTPMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main()) 