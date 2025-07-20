# PTP MCP Server Testing Guide

## Prerequisites

1. **OpenShift Cluster with PTP**
   - Ensure you have access to an OpenShift cluster
   - PTP operator should be installed
   - `openshift-ptp` namespace should exist
   - `oc` CLI should be configured

2. **Python Environment**
   - Python 3.8 or higher
   - All dependencies installed

## Step 1: Basic Setup and Verification

### 1.1 Install Dependencies
```bash
pip install -r requirements.txt
```

### 1.2 Verify OpenShift Access
```bash
oc whoami
oc get namespace openshift-ptp
```

### 1.3 Check PTP Resources
```bash
oc get ptpconfig -n openshift-ptp
oc get pods -n openshift-ptp
```

## Step 2: Test Individual Components

### 2.1 Test Configuration Parser
```bash
python -c "
from ptp_config_parser import PTPConfigParser
import asyncio

async def test():
    parser = PTPConfigParser()
    try:
        configs = await parser.get_ptp_configs()
        print('✓ Configuration parser working')
        print(f'Found {len(configs.get(\"items\", []))} configurations')
    except Exception as e:
        print(f'✗ Configuration parser failed: {e}')

asyncio.run(test())
"
```

### 2.2 Test Log Parser
```bash
python -c "
from ptp_log_parser import PTPLogParser
import asyncio

async def test():
    parser = PTPLogParser()
    try:
        logs = await parser.get_ptp_logs(lines=100)
        print('✓ Log parser working')
        print(f'Retrieved {len(logs)} log entries')
        
        # Test log search
        filtered = parser.search_logs(logs, 'dpll', 'last_hour')
        print(f'Found {len(filtered)} dpll-related logs')
    except Exception as e:
        print(f'✗ Log parser failed: {e}')

asyncio.run(test())
"
```

### 2.3 Test PTP Model
```bash
python -c "
from ptp_model import PTPModel
from ptp_config_parser import PTPConfigParser
import asyncio

async def test():
    model = PTPModel()
    parser = PTPConfigParser()
    
    try:
        config_data = await parser.get_ptp_configs()
        ptp_config = model.create_ptp_configuration(config_data)
        
        print('✓ PTP model working')
        print(f'Clock Type: {ptp_config.clock_type.value}')
        print(f'Domain: {ptp_config.domain}')
        print(f'Clock Class: {ptp_config.clock_class}')
        
        # Test ITU compliance
        compliance = model.validate_itu_t_compliance(ptp_config)
        print(f'ITU-T Compliant: {compliance[\"compliant\"]}')
    except Exception as e:
        print(f'✗ PTP model failed: {e}')

asyncio.run(test())
"
```

## Step 3: Test MCP Tools

### 3.1 Test Individual Tools
```bash
python -c "
from ptp_tools import PTPTools
import asyncio

async def test_tools():
    tools = PTPTools()
    
    # Test 1: Get PTP config
    print('Testing get_ptp_config...')
    result = await tools.get_ptp_config({'namespace': 'openshift-ptp'})
    print(f'✓ Config tool: {result[\"success\"]}')
    
    # Test 2: Get logs
    print('Testing get_ptp_logs...')
    result = await tools.get_ptp_logs({'lines': 100})
    print(f'✓ Logs tool: {result[\"success\"]}')
    
    # Test 3: Search logs
    print('Testing search_logs...')
    result = await tools.search_logs({'query': 'dpll'})
    print(f'✓ Search tool: {result[\"success\"]}')
    
    # Test 4: Health check
    print('Testing check_ptp_health...')
    result = await tools.check_ptp_health({})
    print(f'✓ Health tool: {result[\"success\"]}')

asyncio.run(test_tools())
"
```

### 3.2 Test Natural Language Queries
```bash
python -c "
from ptp_tools import PTPTools
import asyncio

async def test_queries():
    tools = PTPTools()
    
    queries = [
        'What is the current grandmaster?',
        'Show ptpconfig parameters',
        'Check for sync loss',
        'What is the BMCA state?'
    ]
    
    for query in queries:
        print(f'Testing: \"{query}\"')
        result = await tools.query_ptp({'question': query})
        print(f'✓ Query tool: {result[\"success\"]}')
        if result['success']:
            print(f'Response: {result[\"response\"][:100]}...')

asyncio.run(test_queries())
"
```

## Step 4: Test MCP Server

### 4.1 Start the MCP Server
```bash
python ptp_mcp_server.py
```

### 4.2 Test MCP Protocol (using netcat)
```bash
# In another terminal
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | nc localhost 8080
```

## Step 5: API Testing Scripts

### 5.1 Run Comprehensive Tests
```bash
python test_ptp_server.py
```

### 5.2 Run Example Usage
```bash
python example_usage.py
```

## Step 6: Manual API Testing

### 6.1 Test Configuration API
```python
import asyncio
from ptp_tools import PTPTools

async def test_config_api():
    tools = PTPTools()
    
    # Test configuration retrieval
    result = await tools.get_ptp_config({
        "namespace": "openshift-ptp"
    })
    
    print("Configuration API Test:")
    print(f"Success: {result['success']}")
    if result['success']:
        config = result['configuration']
        print(f"Name: {config['name']}")
        print(f"Clock Type: {config['clock_type']}")
        print(f"Domain: {config['domain']}")
        print(f"Clock Class: {config['clock_class']}")
        print(f"Priorities: {config['priorities']}")
    else:
        print(f"Error: {result.get('error')}")

asyncio.run(test_config_api())
```

### 6.2 Test Logs API
```python
import asyncio
from ptp_tools import PTPTools

async def test_logs_api():
    tools = PTPTools()
    
    # Test log retrieval
    result = await tools.get_ptp_logs({
        "namespace": "openshift-ptp",
        "lines": 200
    })
    
    print("Logs API Test:")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Logs Count: {result['logs_count']}")
        print(f"Grandmaster: {result['grandmaster']}")
        print(f"Sync Status: {result['sync_status']}")
    else:
        print(f"Error: {result.get('error')}")

asyncio.run(test_logs_api())
```

### 6.3 Test Search API
```python
import asyncio
from ptp_tools import PTPTools

async def test_search_api():
    tools = PTPTools()
    
    # Test log search
    result = await tools.search_logs({
        "query": "clockClass change",
        "time_range": "last_hour"
    })
    
    print("Search API Test:")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Query: {result['query']}")
        print(f"Total Logs: {result['total_logs']}")
        print(f"Matching Logs: {result['matching_logs']}")
        print(f"Results: {len(result['results'])}")
    else:
        print(f"Error: {result.get('error')}")

asyncio.run(test_search_api())
```

### 6.4 Test Health API
```python
import asyncio
from ptp_tools import PTPTools

async def test_health_api():
    tools = PTPTools()
    
    # Test health check
    result = await tools.check_ptp_health({
        "check_config": True,
        "check_sync": True,
        "check_logs": True
    })
    
    print("Health API Test:")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Overall Status: {result['overall_status']}")
        for check_name, check_result in result['checks'].items():
            print(f"{check_name}: {check_result}")
    else:
        print(f"Error: {result.get('error')}")

asyncio.run(test_health_api())
```

### 6.5 Test Natural Language API
```python
import asyncio
from ptp_tools import PTPTools

async def test_nl_api():
    tools = PTPTools()
    
    # Test natural language query
    result = await tools.query_ptp({
        "question": "What is the current grandmaster?",
        "context": "Testing API"
    })
    
    print("Natural Language API Test:")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Question: {result['question']}")
        print(f"Response: {result['response']}")
        print(f"Query Info: {result['query_info']}")
    else:
        print(f"Error: {result.get('error')}")

asyncio.run(test_nl_api())
```

## Step 7: Expected Results

### 7.1 Successful Configuration Test
```
✓ Configuration parser working
Found 1 configurations
✓ PTP model working
Clock Type: BC
Domain: 24
Clock Class: 248
ITU-T Compliant: True
```

### 7.2 Successful Logs Test
```
✓ Log parser working
Retrieved 150 log entries
Found 25 dpll-related logs
```

### 7.3 Successful Tools Test
```
✓ Config tool: True
✓ Logs tool: True
✓ Search tool: True
✓ Health tool: True
```

### 7.4 Successful Query Test
```
Testing: "What is the current grandmaster?"
✓ Query tool: True
Response: Current grandmaster status: s0 on interface ens7f0...
```

## Step 8: Troubleshooting

### 8.1 Common Issues

**Issue: "oc command not found"**
```bash
# Install OpenShift CLI
curl -L https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/linux/oc.tar.gz | tar xz
sudo mv oc /usr/local/bin/
```

**Issue: "Permission denied"**
```bash
# Ensure proper permissions
chmod +x ptp_mcp_server.py
chmod +x setup.py
```

**Issue: "Module not found"**
```bash
# Install dependencies
pip install -r requirements.txt
```

**Issue: "OpenShift access denied"**
```bash
# Login to OpenShift
oc login --token=<your-token> --server=<your-server>
```

### 8.2 Debug Mode
```bash
# Run with debug logging
PYTHONPATH=. python -u ptp_mcp_server.py
```

## Step 9: Performance Testing

### 9.1 Load Test
```python
import asyncio
import time
from ptp_tools import PTPTools

async def load_test():
    tools = PTPTools()
    start_time = time.time()
    
    # Run multiple queries concurrently
    tasks = []
    for i in range(10):
        task = tools.query_ptp({"question": "What is the current grandmaster?"})
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    
    print(f"Load Test Results:")
    print(f"Total Queries: 10")
    print(f"Successful: {success_count}")
    print(f"Time: {end_time - start_time:.2f} seconds")
    print(f"Average: {(end_time - start_time) / 10:.2f} seconds per query")

asyncio.run(load_test())
```

## Step 10: Ready for Agent Integration

Once all tests pass, your API is ready for agent integration. The key endpoints to integrate are:

1. **Configuration API**: `get_ptp_config()`
2. **Logs API**: `get_ptp_logs()`
3. **Search API**: `search_logs()`
4. **Health API**: `check_ptp_health()`
5. **Natural Language API**: `query_ptp()`

Each API returns structured JSON responses that can be easily consumed by your agent. 