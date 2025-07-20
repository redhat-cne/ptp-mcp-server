# PTP MCP Server

A Model Context Protocol (MCP) server for monitoring and analyzing Precision Time Protocol (PTP) configurations and logs in OpenShift clusters.

## Features

### Core Functionality
- **PTP Configuration Monitoring**: Query and parse ptpconfig resources from the `openshift-ptp` namespace
- **Log Analysis**: Access and analyze linuxptp daemon logs with structured parsing
- **Contextual Model**: Map configurations and runtime status into a consistent PTP model
- **Question-Answering**: Natural language interface for PTP-related queries

### PTP Knowledge Context
- **BMCA (Best Master Clock Algorithm)** understanding and analysis
- **Clock Class** tracking and propagation
- **ITU-T G.8275.1** profile-specific logic (domain 24-43)
- **Timing traceability** and holdover scenario interpretation
- **Offset tracking** and frequency analysis

### Supported Queries
- "What is the current grandmaster?"
- "Show ptpconfig parameters"
- "Check for sync loss"
- "Search logs for clockClass change"
- "Get offset trend in last hour"
- "What is the BMCA state?"
- "Show current clock hierarchy"

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Starting the MCP Server

```bash
python ptp_mcp_server.py
```

### Configuration

The server connects to OpenShift using:
- `oc` command-line tool (must be authenticated)
- Kubernetes API client (fallback)

### Sample Queries

```python
# Get current PTP configuration
await client.call_tool("get_ptp_config", {})

# Search logs for specific patterns
await client.call_tool("search_logs", {
    "query": "clockClass change",
    "time_range": "last_hour"
})

# Get current grandmaster status
await client.call_tool("get_grandmaster_status", {})

# Analyze sync status
await client.call_tool("analyze_sync_status", {})
```

## Architecture

### Components

1. **PTPConfigParser**: Parses OpenShift ptpconfig resources
2. **LogParser**: Analyzes linuxptp daemon logs
3. **PTPModel**: Contextual model combining config and runtime data
4. **QueryEngine**: Natural language processing for PTP queries
5. **MCPTools**: MCP protocol tools for external access

### Data Flow

1. **Configuration Collection**: `oc get ptpconfig -n openshift-ptp -o yaml`
2. **Log Collection**: `oc logs ds/linuxptp-daemon -c linuxptp-daemon-container -n openshift-ptp`
3. **Parsing**: Structured parsing of YAML configs and log entries
4. **Modeling**: Contextual mapping of PTP state
5. **Query Processing**: Natural language to structured query conversion

## PTP Concepts Supported

- **Clock Types**: OC (Ordinary Clock), BC (Boundary Clock), TC (Transparent Clock)
- **BMCA States**: Master, Slave, Passive
- **Sync Status**: Locked, Unlocked, Holdover
- **Clock Class**: Priority and accuracy tracking
- **Offset Analysis**: Frequency and phase offset monitoring
- **ITU-T G.8275.1**: Profile-specific domain and priority rules

## Development

### Adding New Tools

1. Create tool function in `ptp_tools.py`
2. Register in `ptp_mcp_server.py`
3. Add documentation and examples

### Extending PTP Knowledge

1. Update `ptp_model.py` with new PTP concepts
2. Add parsing logic in `log_parser.py`
3. Extend query patterns in `query_engine.py`

## License

MIT License 