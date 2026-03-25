#!/usr/bin/env python3
"""
PTP MCP Server - Model Context Protocol server for OpenShift PTP monitoring

Supports two transport modes:
- stdio: For local MCP clients (Claude Code, Claude Desktop)
- http: For OpenShift Lightspeed integration via streamableHTTP

Usage:
  python ptp_mcp_server.py              # stdio mode (default)
  python ptp_mcp_server.py --http       # HTTP mode on default port 8080
  python ptp_mcp_server.py --http --port 9000  # HTTP mode on custom port

Environment variables:
  PTP_MCP_PORT: Port for HTTP server (default: 8080)
  PTP_MCP_HOST: Host to bind to (default: 0.0.0.0)
"""

import argparse
import asyncio
import json
import logging
import os
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
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
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
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
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
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
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
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        }
                    }
                ),
                Tool(
                    name="analyze_sync_status",
                    description="Analyze PTP synchronization status and health, including optional path delay analysis",
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
                            },
                            "include_path_delay": {
                                "type": "boolean",
                                "default": False,
                                "description": "Include network path delay and asymmetry analysis"
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
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
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
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
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
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
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        },
                        "required": ["question"]
                    }
                ),
                Tool(
                    name="analyze_servo_stability",
                    description="Analyze PI servo controller behavior, detect clockcheck events, and assess stability",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Kubernetes namespace"
                            },
                            "lines": {
                                "type": "integer",
                                "default": 1000,
                                "description": "Number of log lines to analyze"
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        }
                    }
                ),
                Tool(
                    name="analyze_frequency_drift",
                    description="Detect and trend frequency adjustments over time",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Kubernetes namespace"
                            },
                            "window_minutes": {
                                "type": "integer",
                                "default": 60,
                                "description": "Time window in minutes for analysis"
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        }
                    }
                ),
                Tool(
                    name="analyze_holdover",
                    description="Track and analyze holdover behavior and events",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Kubernetes namespace"
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        }
                    }
                ),
                Tool(
                    name="get_gnss_status",
                    description="Get detailed GNSS receiver status and quality metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Kubernetes namespace"
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        }
                    }
                ),
                Tool(
                    name="get_port_status",
                    description="Get PTP port states and transition history",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Kubernetes namespace"
                            },
                            "interface": {
                                "type": "string",
                                "description": "Specific interface to check (optional)"
                            },
                            "include_history": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include transition history"
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        }
                    }
                ),
                Tool(
                    name="run_pmc_query",
                    description="Execute PMC (PTP Management Client) queries for real-time PTP data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "enum": ["PARENT_DATA_SET", "DEFAULT_DATA_SET", "CURRENT_DATA_SET", "TIME_PROPERTIES_DATA_SET", "PORT_DATA_SET", "GRANDMASTER_SETTINGS_NP"],
                                "default": "PARENT_DATA_SET",
                                "description": "PMC command to execute"
                            },
                            "namespace": {
                                "type": "string",
                                "default": "openshift-ptp",
                                "description": "Kubernetes namespace"
                            },
                            "config_file": {
                                "type": "string",
                                "default": "/var/run/ptp4l.0.config",
                                "description": "Path to ptp4l config file in the pod"
                            },
                            "kubeconfig": {
                                "type": "string",
                                "description": "MUST be base64-encoded kubeconfig content. To target a different cluster, the kubeconfig file must first be base64 encoded using: cat kubeconfig.yaml | base64 -w0. Then pass the resulting base64 string here. Optional - if not provided, uses the default cluster."
                            }
                        }
                    }
                ),
            ]
            return ListToolsResult(tools=tools)

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls for PTP operations"""
            safe_args = {k: ("***" if k == "kubeconfig" else v) for k, v in arguments.items()}
            logger.info(f"Tool call received: {name} with args: {safe_args}")
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
                elif name == "analyze_servo_stability":
                    result = await self.ptp_tools.analyze_servo_stability(arguments)
                elif name == "analyze_frequency_drift":
                    result = await self.ptp_tools.analyze_frequency_drift(arguments)
                elif name == "analyze_holdover":
                    result = await self.ptp_tools.analyze_holdover(arguments)
                elif name == "get_gnss_status":
                    result = await self.ptp_tools.get_gnss_status(arguments)
                elif name == "get_port_status":
                    result = await self.ptp_tools.get_port_status(arguments)
                elif name == "run_pmc_query":
                    result = await self.ptp_tools.run_pmc_query(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

                logger.info(f"Tool {name} completed successfully")
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )

    def _get_init_options(self) -> InitializationOptions:
        """Get initialization options for the MCP server"""
        return InitializationOptions(
            server_name="ptp-mcp-server",
            server_version="1.0.0",
            capabilities=self.server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )

    async def run_stdio(self):
        """Run the MCP server in stdio mode (for local MCP clients)"""
        logger.info("Starting PTP MCP Server in stdio mode")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self._get_init_options(),
            )

    async def run_http(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the MCP server in HTTP mode (for OpenShift Lightspeed)"""
        try:
            from mcp.server.sse import SseServerTransport
            from starlette.responses import JSONResponse
            import uvicorn
        except ImportError as e:
            logger.error(f"HTTP mode requires additional dependencies: {e}")
            logger.error("Install with: pip install starlette uvicorn sse-starlette")
            sys.exit(1)

        # Create SSE transport
        # The endpoint parameter is where clients POST messages back
        sse_transport = SseServerTransport("/mcp/messages")

        # Store reference to self for use in ASGI app
        mcp_server = self.server
        init_options = self._get_init_options()

        async def app(scope, receive, send):
            """Custom ASGI application for MCP server"""
            path = scope.get("path", "")
            method = scope.get("method", "")

            if path == "/health" and method == "GET":
                response = JSONResponse({"status": "healthy", "server": "ptp-mcp-server"})
                await response(scope, receive, send)
            elif path == "/ready" and method == "GET":
                response = JSONResponse({"status": "ready", "server": "ptp-mcp-server"})
                await response(scope, receive, send)
            elif path == "/mcp" and method == "GET":
                # SSE endpoint - connect_sse handles the response
                logger.info(f"SSE connection from {scope.get('client', 'unknown')}")
                async with sse_transport.connect_sse(scope, receive, send) as streams:
                    await mcp_server.run(
                        streams[0],
                        streams[1],
                        init_options,
                    )
            elif path == "/mcp/messages" and method == "POST":
                # POST messages - handle_post_message handles the response
                logger.info(f"POST message from {scope.get('client', 'unknown')}")
                await sse_transport.handle_post_message(scope, receive, send)
            else:
                # 404 Not Found
                response = JSONResponse({"error": "Not found"}, status_code=404)
                await response(scope, receive, send)

        logger.info(f"Starting PTP MCP Server in HTTP mode on {host}:{port}")
        logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
        logger.info(f"Health check: http://{host}:{port}/health")

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="PTP MCP Server for OpenShift PTP monitoring"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP mode for OpenShift Lightspeed (default: stdio mode)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for HTTP server (default: 8080, or PTP_MCP_PORT env var)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind HTTP server (default: 0.0.0.0, or PTP_MCP_HOST env var)"
    )
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()
    server = PTPMCPServer()

    if args.http:
        # HTTP mode for OpenShift Lightspeed
        host = args.host or os.environ.get("PTP_MCP_HOST", "0.0.0.0")
        port_str = os.environ.get("PTP_MCP_PORT", "8080")
        try:
            port = args.port or int(port_str)
        except ValueError:
            logger.error(f"Invalid PTP_MCP_PORT value: {port_str}")
            sys.exit(1)
        await server.run_http(host=host, port=port)
    else:
        # stdio mode for local MCP clients
        await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
