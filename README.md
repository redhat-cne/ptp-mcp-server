# PTP MCP Server

A Model Context Protocol (MCP) server for monitoring and analyzing Precision Time Protocol (PTP) systems in OpenShift clusters.

## 🚀 Features

- **PTP Configuration Analysis**: Parse and validate PTP configurations from OpenShift
- **Real-time Log Monitoring**: Access linuxptp daemon logs with intelligent parsing
- **Natural Language Queries**: Ask questions about PTP status in plain English
- **Health Monitoring**: Comprehensive PTP system health checks
- **Synchronization Analysis**: Monitor sync status, offsets, and BMCA state
- **Clock Hierarchy**: Track grandmaster and clock hierarchy information
- **ITU-T Compliance**: Validate configurations against ITU-T G.8275.1 standards

## 📋 Prerequisites

- Python 3.8 or higher
- OpenShift CLI (`oc`) installed and configured
- Access to OpenShift cluster with PTP operator installed
- PTP namespace (`openshift-ptp`) exists

## 🛠️ Source Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/redhat-cne/ptp-mcp-server.git
   cd ptp-mcp-server
   ```

## To Deploy For Quick Tests
 
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify OpenShift access**:
   ```bash
   export KUBECONFIG=/path/to/kubeconfig
   oc whoami
   oc get namespace openshift-ptp
   ```

3. **Quick Testing**

Run the comprehensive test suite:

```bash
export KUBECONFIG=/path/to/kubeconfig
python quick_test.py
```

Expected output:
```
🔍 PTP MCP Server API Quick Test
==================================================
Tests Passed: 8/8
Success Rate: 100.0%
🎉 ALL TESTS PASSED! Your API is ready for agent integration.
```

## 🔧 MCP Server

The MCP server supports two transport modes:
- **stdio**: For local MCP clients (Claude Code, Claude Desktop)
- **HTTP/SSE**: For OpenShift Lightspeed integration

### Local Usage (stdio mode)

```bash
python ptp_mcp_server.py
```

### Remote Usage (http mode)

```bash
# Default port 8080
python ptp_mcp_server.py --http

# Custom port
python ptp_mcp_server.py --http --port 9000

# Or use environment variable
PTP_MCP_PORT=9000 python ptp_mcp_server.py --http
```

### Deploy to OpenShift

```bash
podman build -t quay.io/$USER/ptp-mcp-server:latest .
podman push quay.io/$USER/ptp-mcp-server:latest
cd k8s && kustomize edit set image quay.io/redhat-cne/ptp-mcp-server=quay.io/$USER/ptp-mcp-server:latest && cd ..
oc apply -k k8s/
```

#### Configure in OpenShift Lightspeed

Add the MCP server to your OLSConfig:

```yaml
apiVersion: ols.openshift.io/v1alpha1
kind: OLSConfig
metadata:
  name: cluster
spec:
  featureGates:
  - MCPServer
  mcpServers:
  - name: ptp-monitoring
    url: 'http://ptp-mcp-server.openshift-ptp.svc.cluster.local:8080/mcp'
    timeout: 30
```

#### Usage in OpenShift Lightspeed

By default, the MCP server assumes that it is running on the cluster that is to
be monitored/queried.  Any tool use will target the local cluster.  However, if
the MCP server is running on a hub cluster and the user intends for its prompt
to target spoke cluster then OLS context should include a base64 copy of the
kubeconfig for the spoke cluster.

**note:** It is important to use a minimal kubeconfig that is token based rather
than a client certificate based kubeconfig as the OLS context size will not
allow for a larger kubeconfig value.

The following example generates such a kubeconfig for lab testing purposes.  In
a production environment care should be taken to limit the service account
permissions to only the strict minimum RBAC policies required.

```bash
oc create sa ols-ptp-user -n default 2>/dev/null
oc adm policy add-cluster-role-to-user cluster-admin -z ols-ptp-user -n default
TOKEN=$(oc create token ols-ptp-user -n default --duration=24h)
API_SERVER=$(oc whoami --show-server)
cat << EOF > minimal-kubeconfig.yaml
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: ${API_SERVER}
    insecure-skip-tls-verify: true
  name: cluster
contexts:
- context:
    cluster: cluster
    user: user
  name: ctx
current-context: ctx
users:
- name: user
  user:
    token: ${TOKEN}
EOF
```

## 📚 API Endpoints

### 1. Configuration API
```python
from ptp_tools import PTPTools
tools = PTPTools()
result = await tools.get_ptp_config({"namespace": "openshift-ptp"})
```

### 2. Logs API
```python
result = await tools.get_ptp_logs({"lines": 1000})
```

### 3. Search API
```python
result = await tools.search_logs({"query": "dpll", "time_range": "last_hour"})
```

### 4. Health API
```python
result = await tools.check_ptp_health({"check_config": True, "check_sync": True})
```

### 5. Natural Language API
```python
result = await tools.query_ptp({"question": "What is the current grandmaster?"})
```

### 6. Grandmaster Status API
```python
result = await tools.get_grandmaster_status({"detailed": True})
```

### 7. Sync Status API
```python
result = await tools.analyze_sync_status({"include_offsets": True})
```

### 8. Clock Hierarchy API
```python
result = await tools.get_clock_hierarchy({"include_ports": True})
```

## 🚀 Usage Examples

### Basic Health Check
```python
import asyncio
from ptp_tools import PTPTools

async def check_health():
    tools = PTPTools()
    health = await tools.check_ptp_health({})
    
    if health["success"]:
        print(f"Status: {health['overall_status']}")
        for check_name, result in health["checks"].items():
            print(f"{check_name}: {result}")
    else:
        print(f"Error: {health.get('error')}")

asyncio.run(check_health())
```

### Natural Language Query
```python
async def ask_question():
    tools = PTPTools()
    response = await tools.query_ptp({
        "question": "What is the current grandmaster?"
    })
    
    if response["success"]:
        print(f"Answer: {response['response']}")
    else:
        print(f"Error: {response.get('error')}")

asyncio.run(ask_question())
```

### Log Analysis
```python
async def analyze_logs():
    tools = PTPTools()
    
    # Get recent logs
    logs = await tools.get_ptp_logs({"lines": 500})
    
    # Search for specific events
    sync_loss = await tools.search_logs({"query": "sync loss"})
    clock_changes = await tools.search_logs({"query": "clockClass change"})
    
    print(f"Total logs: {logs['logs_count']}")
    print(f"Sync loss events: {sync_loss['matching_logs']}")
    print(f"Clock changes: {clock_changes['matching_logs']}")

asyncio.run(analyze_logs())
```

### MCP Tools Available

| Tool | Description |
|------|-------------|
| `get_ptp_config` | Get PTP configuration |
| `get_ptp_logs` | Get linuxptp daemon logs |
| `search_logs` | Search logs for patterns |
| `get_grandmaster_status` | Get grandmaster info |
| `analyze_sync_status` | Analyze sync status |
| `get_clock_hierarchy` | Get clock hierarchy |
| `check_ptp_health` | Comprehensive health check |
| `query_ptp` | Natural language interface |
| `analyze_servo_stability` | PI servo controller analysis |
| `analyze_holdover` | Holdover event analysis |
| `get_gnss_status` | GNSS receiver status |
| `get_port_status` | PTP port state tracking |
| `run_pmc_query` | Execute PMC commands |

### Deployment Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image with Python + oc CLI |
| `k8s/rbac.yaml` | ServiceAccount, ClusterRole, ClusterRoleBinding |
| `k8s/deployment.yaml` | Deployment with health checks |
| `k8s/service.yaml` | ClusterIP Service |
| `k8s/olsconfig-example.yaml` | Example OLS configuration |
| `k8s/kustomization.yaml` | Deploy all with `oc apply -k k8s/` |

### RBAC Permissions

The ServiceAccount is granted these permissions:

| Resource | Verbs | Purpose |
|----------|-------|---------|
| `ptpconfigs`, `ptpoperatorconfigs` | get, list, watch | Read PTP configurations |
| `pods` | get, list, watch | Find linuxptp-daemon pods |
| `pods/log` | get, list | Read daemon logs |
| `pods/exec` | create | Execute PMC queries |
| `namespaces` | get, list | Namespace access |
| `nodes` | get, list | Node topology (optional) |

## 📊 Performance

- **Average Response Time**: 0.78s
- **Fastest API**: Configuration API (0.22s)
- **Concurrent Operations**: 4/4 successful in 2.45s
- **Success Rate**: 100% (8/8 endpoints)

## 🏗️ Architecture

```
ptp-mcp-server/
├── ptp_mcp_server.py      # Main MCP server (stdio + HTTP modes)
├── ptp_config_parser.py   # PTP configuration parser
├── ptp_log_parser.py      # Linuxptp log parser
├── ptp_model.py           # PTP data models
├── ptp_query_engine.py    # Natural language query engine
├── ptp_tools.py           # API endpoint implementations
├── quick_test.py          # Quick test suite
├── performance_test.py    # Performance benchmarking
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container image definition
└── k8s/                   # Kubernetes/OpenShift manifests
    ├── kustomization.yaml # Kustomize configuration
    ├── rbac.yaml          # ServiceAccount & RBAC
    ├── deployment.yaml    # Deployment specification
    ├── service.yaml       # Service definition
    └── olsconfig-example.yaml  # OLS integration example
```

## 🔍 PTP Concepts Supported

- **BMCA (Best Master Clock Algorithm)**: Clock selection and hierarchy
- **Clock Types**: OC (Ordinary Clock), BC (Boundary Clock), TC (Transparent Clock)
- **ITU-T G.8275.1**: Profile compliance and validation
- **Synchronization**: Offset tracking, frequency adjustment, sync status
- **Grandmaster**: Primary time source identification and status
- **Clock Class**: Quality and traceability indicators
- **Domain Numbers**: PTP domain configuration (24-43 for ITU-T)

## 🧪 Testing

### Run All Tests
```bash
python quick_test.py
```

### Performance Testing
```bash
python performance_test.py
```

### Individual Component Testing
```bash
# Test configuration parser
python -c "from ptp_config_parser import PTPConfigParser; import asyncio; asyncio.run(PTPConfigParser().get_ptp_configs())"

# Test log parser
python -c "from ptp_log_parser import PTPLogParser; import asyncio; asyncio.run(PTPLogParser().get_ptp_logs())"
```

## 📖 Documentation

- [Testing Guide](testing_guide.md) - Comprehensive testing instructions
- [Agent Integration Guide](agent_integration_guide.md) - Integration examples for agents
- [Testing Steps](TESTING_STEPS.md) - Step-by-step testing process
- [Testing Results](TESTING_RESULTS.md) - Complete test results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenShift PTP Operator team
- Linuxptp project
- Model Context Protocol (MCP) community

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the [testing documentation](TESTING_STEPS.md)
- Review the [agent integration guide](agent_integration_guide.md)

---

**Status**: ✅ Production Ready  
**Last Updated**: January 2025  
**Version**: 1.0.0 
