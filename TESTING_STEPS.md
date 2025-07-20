# PTP MCP Server API Testing Steps

## 🚀 Quick Start (5 minutes)

### Step 1: Run Quick Test
```bash
python quick_test.py
```
**Expected Result**: All 8 tests should pass with 100% success rate.

### Step 2: Verify Prerequisites
```bash
# Check OpenShift access
oc whoami

# Check PTP namespace
oc get namespace openshift-ptp

# Check PTP resources
oc get ptpconfig -n openshift-ptp
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

## 📋 Complete Testing Checklist

### ✅ Prerequisites Check
- [ ] Python 3.8+ installed
- [ ] OpenShift CLI (`oc`) installed and configured
- [ ] Access to OpenShift cluster with PTP operator
- [ ] Dependencies installed (`pip install -r requirements.txt`)

### ✅ Basic Component Tests
- [ ] Configuration parser working
- [ ] Log parser working
- [ ] PTP model working
- [ ] Query engine working

### ✅ API Endpoint Tests
- [ ] Configuration API (`get_ptp_config`)
- [ ] Logs API (`get_ptp_logs`)
- [ ] Search API (`search_logs`)
- [ ] Health API (`check_ptp_health`)
- [ ] Natural Language API (`query_ptp`)
- [ ] Grandmaster Status API (`get_grandmaster_status`)
- [ ] Sync Status API (`analyze_sync_status`)
- [ ] Clock Hierarchy API (`get_clock_hierarchy`)

### ✅ Integration Tests
- [ ] MCP server starts without errors
- [ ] All tools respond correctly
- [ ] Error handling works properly
- [ ] Performance is acceptable

## 🔧 Detailed Testing Steps

### 1. Environment Setup
```bash
# Clone/checkout the project
cd ptp-mcp-server

# Install dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x ptp_mcp_server.py setup.py
```

### 2. OpenShift Verification
```bash
# Test OpenShift access
oc whoami
# Should return your username

# Test PTP namespace
oc get namespace openshift-ptp
# Should show the namespace exists

# Test PTP resources
oc get ptpconfig -n openshift-ptp
# Should show PTP configurations

# Test PTP pods
oc get pods -n openshift-ptp
# Should show running PTP daemon pods
```

### 3. Component Testing
```bash
# Test configuration parser
python -c "
from ptp_config_parser import PTPConfigParser
import asyncio
async def test():
    parser = PTPConfigParser()
    configs = await parser.get_ptp_configs()
    print(f'Found {len(configs.get(\"items\", []))} configurations')
asyncio.run(test())
"

# Test log parser
python -c "
from ptp_log_parser import PTPLogParser
import asyncio
async def test():
    parser = PTPLogParser()
    logs = await parser.get_ptp_logs(lines=100)
    print(f'Retrieved {len(logs)} log entries')
asyncio.run(test())
"
```

### 4. API Testing
```bash
# Run comprehensive API test
python quick_test.py

# Expected output:
# Tests Passed: 8/8
# Success Rate: 100.0%
# ALL TESTS PASSED! Your API is ready for agent integration.
```

### 5. MCP Server Testing
```bash
# Start the MCP server
python ptp_mcp_server.py

# In another terminal, test MCP protocol
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | nc localhost 8080
```

### 6. Performance Testing
```python
# Run performance test
python -c "
import asyncio
import time
from ptp_tools import PTPTools

async def perf_test():
    tools = PTPTools()
    start = time.time()
    
    # Test concurrent operations
    results = await asyncio.gather(*[
        tools.get_ptp_config({}),
        tools.get_ptp_logs({'lines': 100}),
        tools.check_ptp_health({}),
        tools.query_ptp({'question': 'What is the current grandmaster?'})
    ])
    
    end = time.time()
    success_count = sum(1 for r in results if r.get('success'))
    
    print(f'Performance Test: {success_count}/4 successful in {end-start:.2f}s')

asyncio.run(perf_test())
"
```

## 🧪 Sample Data Testing (No Cluster Required)

If you don't have access to an OpenShift cluster, the system will fall back to sample data:

```bash
python quick_test.py
# Will show sample data demonstration
```

## 📊 Expected Results

### Successful Test Output
```
🔍 PTP MCP Server API Quick Test
==================================================

1️⃣ Testing Configuration API...
✅ Configuration API: PASSED
   - Name: bc-config-1
   - Clock Type: BC
   - Domain: 24

2️⃣ Testing Logs API...
✅ Logs API: PASSED
   - Logs Count: 150
   - Grandmaster: s0

3️⃣ Testing Search API...
✅ Search API: PASSED
   - Total Logs: 1000
   - Matching Logs: 25

4️⃣ Testing Health API...
✅ Health API: PASSED
   - Overall Status: healthy

5️⃣ Testing Natural Language API...
✅ Natural Language API: PASSED
   - Response: Current grandmaster status: s0...

6️⃣ Testing Grandmaster Status API...
✅ Grandmaster Status API: PASSED
   - Status: s0
   - Interface: ens7f0

7️⃣ Testing Sync Status API...
✅ Sync Status API: PASSED
   - DPLL Locked: True
   - Offset in Range: True

8️⃣ Testing Clock Hierarchy API...
✅ Clock Hierarchy API: PASSED
   - Clock Type: BC
   - Domain: 24

==================================================
📊 TEST SUMMARY
==================================================
Tests Passed: 8/8
Success Rate: 100.0%

🎉 ALL TESTS PASSED! Your API is ready for agent integration.
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### Issue: "oc command not found"
```bash
# Install OpenShift CLI
curl -L https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/linux/oc.tar.gz | tar xz
sudo mv oc /usr/local/bin/
```

#### Issue: "Permission denied"
```bash
# Fix permissions
chmod +x ptp_mcp_server.py setup.py
```

#### Issue: "Module not found"
```bash
# Install dependencies
pip install -r requirements.txt
```

#### Issue: "OpenShift access denied"
```bash
# Login to OpenShift
oc login --token=<your-token> --server=<your-server>
```

#### Issue: "PTP namespace not found"
```bash
# Check if PTP operator is installed
oc get operators -n openshift-operators | grep ptp
```

## 🔍 Debug Mode

For detailed debugging:

```bash
# Run with debug logging
PYTHONPATH=. python -u ptp_mcp_server.py

# Or run individual components with debug
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from ptp_tools import PTPTools
import asyncio

async def debug_test():
    tools = PTPTools()
    result = await tools.get_ptp_config({})
    print(result)

asyncio.run(debug_test())
"
```

## 📈 Performance Benchmarks

### Expected Performance
- **Configuration API**: < 2 seconds
- **Logs API**: < 5 seconds (1000 lines)
- **Search API**: < 3 seconds
- **Health API**: < 4 seconds
- **Natural Language API**: < 3 seconds

### Load Testing
```python
import asyncio
import time
from ptp_tools import PTPTools

async def load_test():
    tools = PTPTools()
    start_time = time.time()
    
    # Run 10 concurrent queries
    tasks = []
    for i in range(10):
        task = tools.query_ptp({"question": "What is the current grandmaster?"})
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    
    print(f"Load Test: {success_count}/10 successful in {end_time - start_time:.2f}s")

asyncio.run(load_test())
```

## ✅ Ready for Agent Integration

Once all tests pass, your API is ready for agent integration:

### Available Endpoints
1. `get_ptp_config()` - Get PTP configuration
2. `get_ptp_logs()` - Get linuxptp daemon logs
3. `search_logs()` - Search logs for patterns
4. `get_grandmaster_status()` - Get grandmaster info
5. `analyze_sync_status()` - Analyze sync status
6. `get_clock_hierarchy()` - Get clock hierarchy
7. `check_ptp_health()` - Comprehensive health check
8. `query_ptp()` - Natural language interface

### Response Format
All APIs return structured JSON:
```json
{
  "success": true,
  "data": {...},
  "error": null
}
```

### Next Steps
1. Start the MCP server: `python ptp_mcp_server.py`
2. Integrate with your agent using the endpoints above
3. Use structured JSON responses for agent processing
4. Monitor performance and handle errors gracefully

Your PTP MCP server API is now ready for production use with your agent! 🎉 