# PTP MCP Server Agent Integration Guide

## Quick Start Testing

### Step 1: Run Quick Test
```bash
python quick_test.py
```

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

## API Endpoints for Agent Integration

### 1. Configuration API
```python
from ptp_tools import PTPTools
import asyncio

async def get_config():
    tools = PTPTools()
    result = await tools.get_ptp_config({"namespace": "openshift-ptp"})
    return result

# Usage
config = await get_config()
if config["success"]:
    print(f"Clock Type: {config['configuration']['clock_type']}")
    print(f"Domain: {config['configuration']['domain']}")
```

### 2. Logs API
```python
async def get_logs():
    tools = PTPTools()
    result = await tools.get_ptp_logs({"lines": 500})
    return result

# Usage
logs = await get_logs()
if logs["success"]:
    print(f"Logs Count: {logs['logs_count']}")
    print(f"Grandmaster: {logs['grandmaster']}")
```

### 3. Search API
```python
async def search_logs(query, time_range="last_hour"):
    tools = PTPTools()
    result = await tools.search_logs({
        "query": query,
        "time_range": time_range
    })
    return result

# Usage
results = await search_logs("clockClass change")
if results["success"]:
    print(f"Found {results['matching_logs']} matches")
```

### 4. Health API
```python
async def check_health():
    tools = PTPTools()
    result = await tools.check_ptp_health({
        "check_config": True,
        "check_sync": True,
        "check_logs": True
    })
    return result

# Usage
health = await check_health()
if health["success"]:
    print(f"Status: {health['overall_status']}")
```

### 5. Natural Language API
```python
async def query_ptp(question):
    tools = PTPTools()
    result = await tools.query_ptp({"question": question})
    return result

# Usage
response = await query_ptp("What is the current grandmaster?")
if response["success"]:
    print(f"Answer: {response['response']}")
```

## Agent Integration Examples

### Example 1: Basic Health Monitor Agent
```python
import asyncio
from ptp_tools import PTPTools

class PTPHealthMonitor:
    def __init__(self):
        self.tools = PTPTools()
    
    async def monitor_health(self):
        """Monitor PTP health and alert on issues"""
        health = await self.tools.check_ptp_health({})
        
        if health["success"]:
            status = health["overall_status"]
            if status == "healthy":
                return {"status": "OK", "message": "PTP system is healthy"}
            elif status == "warning":
                return {"status": "WARNING", "message": "PTP system has warnings"}
            else:
                return {"status": "CRITICAL", "message": "PTP system has issues"}
        else:
            return {"status": "ERROR", "message": f"Health check failed: {health.get('error')}"}
    
    async def get_sync_status(self):
        """Get synchronization status"""
        sync = await self.tools.analyze_sync_status({})
        
        if sync["success"]:
            sync_status = sync["sync_status"]
            if sync_status.get("dpll_locked") and sync_status.get("offset_in_range"):
                return {"status": "SYNCED", "message": "Clock is synchronized"}
            else:
                return {"status": "UNSYNCED", "message": "Clock is not synchronized"}
        else:
            return {"status": "ERROR", "message": f"Sync check failed: {sync.get('error')}"}

# Usage
async def main():
    monitor = PTPHealthMonitor()
    
    health = await monitor.monitor_health()
    print(f"Health: {health}")
    
    sync = await monitor.get_sync_status()
    print(f"Sync: {sync}")

asyncio.run(main())
```

### Example 2: Log Analysis Agent
```python
class PTPLogAnalyzer:
    def __init__(self):
        self.tools = PTPTools()
    
    async def analyze_recent_logs(self):
        """Analyze recent logs for issues"""
        logs = await self.tools.get_ptp_logs({"lines": 1000})
        
        if not logs["success"]:
            return {"error": logs.get("error")}
        
        # Search for common issues
        issues = []
        
        # Check for sync loss
        sync_loss = await self.tools.search_logs({"query": "sync loss"})
        if sync_loss["success"] and sync_loss["matching_logs"] > 0:
            issues.append("Sync loss detected")
        
        # Check for clock class changes
        clock_changes = await self.tools.search_logs({"query": "clockClass change"})
        if clock_changes["success"] and clock_changes["matching_logs"] > 0:
            issues.append("Clock class changes detected")
        
        # Check for errors
        errors = await self.tools.search_logs({"query": "error", "log_level": "error"})
        if errors["success"] and errors["matching_logs"] > 0:
            issues.append(f"{errors['matching_logs']} errors detected")
        
        return {
            "total_logs": logs["logs_count"],
            "issues": issues,
            "grandmaster": logs["grandmaster"],
            "sync_status": logs["sync_status"]
        }

# Usage
async def analyze_logs():
    analyzer = PTPLogAnalyzer()
    analysis = await analyzer.analyze_recent_logs()
    print(f"Analysis: {analysis}")

asyncio.run(analyze_logs())
```

### Example 3: Configuration Validator Agent
```python
class PTPConfigValidator:
    def __init__(self):
        self.tools = PTPTools()
    
    async def validate_configuration(self):
        """Validate PTP configuration"""
        config = await self.tools.get_ptp_config({})
        
        if not config["success"]:
            return {"error": config.get("error")}
        
        issues = []
        warnings = []
        
        # Check ITU compliance
        itu_compliance = config.get("itu_compliance", {})
        if not itu_compliance.get("compliant", True):
            issues.extend(itu_compliance.get("errors", []))
        
        warnings.extend(itu_compliance.get("warnings", []))
        
        # Check configuration validation
        validation = config.get("validation", {})
        if not validation.get("valid", True):
            issues.extend(validation.get("errors", []))
        
        warnings.extend(validation.get("warnings", []))
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "configuration": config["configuration"]
        }

# Usage
async def validate_config():
    validator = PTPConfigValidator()
    validation = await validator.validate_configuration()
    print(f"Validation: {validation}")

asyncio.run(validate_config())
```

### Example 4: Natural Language Query Agent
```python
class PTPQueryAgent:
    def __init__(self):
        self.tools = PTPTools()
    
    async def ask_question(self, question):
        """Ask a natural language question about PTP"""
        response = await self.tools.query_ptp({"question": question})
        
        if response["success"]:
            return {
                "answer": response["response"],
                "query_info": response["query_info"],
                "data": response["data"]
            }
        else:
            return {"error": response.get("error")}
    
    async def get_suggestions(self):
        """Get suggested questions"""
        response = await self.tools.query_ptp({"question": ""})
        return response.get("suggestions", [])

# Usage
async def ask_questions():
    agent = PTPQueryAgent()
    
    questions = [
        "What is the current grandmaster?",
        "Show ptpconfig parameters",
        "Check for sync loss",
        "What is the BMCA state?"
    ]
    
    for question in questions:
        answer = await agent.ask_question(question)
        print(f"Q: {question}")
        print(f"A: {answer['answer']}")
        print()

asyncio.run(ask_questions())
```

## Response Format Reference

### Standard API Response Format
```json
{
  "success": true,
  "configuration": {...},
  "logs_count": 150,
  "grandmaster": {...},
  "sync_status": {...},
  "error": null
}
```

### Error Response Format
```json
{
  "success": false,
  "error": "Error message",
  "configuration": null
}
```

### Configuration Response
```json
{
  "success": true,
  "configuration": {
    "name": "bc-config-1",
    "clock_type": "BC",
    "domain": 24,
    "priorities": {"priority1": 128, "priority2": 128},
    "clock_class": 248,
    "sync_intervals": {...},
    "thresholds": {...}
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  },
  "itu_compliance": {
    "compliant": true,
    "errors": [],
    "warnings": []
  }
}
```

### Logs Response
```json
{
  "success": true,
  "logs_count": 150,
  "grandmaster": {
    "status": "s0",
    "interface": "ens7f0",
    "offset": -12,
    "frequency": -6701
  },
  "sync_status": {
    "dpll_locked": true,
    "gnss_available": true,
    "offset_in_range": true,
    "last_offset": -2
  },
  "log_entries": [...]
}
```

### Health Response
```json
{
  "success": true,
  "overall_status": "healthy",
  "checks": {
    "configuration": {
      "valid": true,
      "itu_compliant": true
    },
    "synchronization": {
      "dpll_locked": true,
      "offset_in_range": true
    },
    "logs": {
      "total_logs": 150,
      "error_count": 0,
      "warning_count": 0
    }
  }
}
```

## Testing Your Agent Integration

### 1. Test Individual APIs
```python
import asyncio
from ptp_tools import PTPTools

async def test_apis():
    tools = PTPTools()
    
    # Test each API
    apis = [
        ("Configuration", tools.get_ptp_config({})),
        ("Logs", tools.get_ptp_logs({"lines": 100})),
        ("Health", tools.check_ptp_health({})),
        ("Query", tools.query_ptp({"question": "What is the current grandmaster?"}))
    ]
    
    for name, api_call in apis:
        try:
            result = await api_call
            print(f"{name}: {'✅' if result['success'] else '❌'}")
        except Exception as e:
            print(f"{name}: ❌ {e}")

asyncio.run(test_apis())
```

### 2. Test Error Handling
```python
async def test_error_handling():
    tools = PTPTools()
    
    # Test with invalid parameters
    result = await tools.get_ptp_config({"namespace": "invalid-namespace"})
    print(f"Error handling: {'✅' if not result['success'] else '❌'}")
    
    # Test with invalid query
    result = await tools.search_logs({"query": ""})
    print(f"Empty query handling: {'✅' if result['success'] else '❌'}")

asyncio.run(test_error_handling())
```

## Performance Considerations

### 1. Async Operations
```python
# Good: Run multiple operations concurrently
async def get_all_data():
    tools = PTPTools()
    
    # Run all operations concurrently
    config, logs, health = await asyncio.gather(
        tools.get_ptp_config({}),
        tools.get_ptp_logs({"lines": 100}),
        tools.check_ptp_health({})
    )
    
    return {"config": config, "logs": logs, "health": health}
```

### 2. Caching
```python
import time
from functools import lru_cache

class CachedPTPTools:
    def __init__(self):
        self.tools = PTPTools()
        self.cache = {}
        self.cache_timeout = 30  # seconds
    
    async def get_ptp_config(self, params):
        cache_key = f"config_{hash(str(params))}"
        now = time.time()
        
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if now - cached_time < self.cache_timeout:
                return cached_data
        
        result = await self.tools.get_ptp_config(params)
        self.cache[cache_key] = (now, result)
        return result
```

## Ready for Production

Once you've tested all APIs and integrated them with your agent:

1. **Start the MCP server**: `python ptp_mcp_server.py`
2. **Monitor performance**: Use the caching and async patterns above
3. **Handle errors gracefully**: Always check the `success` field
4. **Log responses**: For debugging and monitoring
5. **Set up alerts**: Based on health status and sync issues

Your agent can now monitor PTP systems, analyze configurations, track synchronization, and provide natural language answers about PTP status! 