# OpenShift PTP Troubleshooting Guide

This guide covers PTP (Precision Time Protocol) monitoring, diagnostics, and troubleshooting for OpenShift clusters using the PTP Operator. It is designed for both operators seeking quick answers and engineers requiring deep technical detail.

> **What Makes This Guide Unique:**
> - **MCP Tool Integration** - Automated diagnostic tools that replace manual commands
> - **Advanced Log Pattern Analysis** - Detailed regex patterns for interpreting linuxptp logs
> - **Deep Troubleshooting Workflows** - Decision trees and failure mode diagnosis
> - **Servo/Clockcheck Analysis** - Understanding and fixing timing instability
>
> For basic PtpConfig configuration examples and CRD reference, see the [Official Red Hat PTP Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/networking/using-ptp-hardware).

---

## MCP Tools Reference

The PTP MCP Server provides automated diagnostic tools that can be invoked to gather and analyze PTP data. When troubleshooting PTP issues, use these MCP tools instead of running manual commands.

### Core MCP Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `get_ptp_config` | Retrieve PTP configuration from OpenShift | Checking ptpconfig settings, validating ITU-T compliance |
| `get_ptp_logs` | Fetch and parse PTP daemon logs | Initial log review, getting structured log data |
| `search_logs` | Search logs for specific patterns | Finding specific errors, filtering by time range or log level |
| `get_grandmaster_status` | Get current grandmaster information | Checking GM identity, clock class, BMCA state |
| `analyze_sync_status` | Analyze synchronization status | Checking if PTP is locked, reviewing offset trends |
| `get_clock_hierarchy` | Get clock hierarchy and port info | Understanding clock relationships, port configurations |
| `check_ptp_health` | Comprehensive health check | Quick overall status assessment, identifying issues |
| `query_ptp` | Natural language query interface | Asking questions about PTP status in plain English |

### Advanced Diagnostic MCP Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `analyze_servo_stability` | Analyze servo controller behavior | Investigating clockcheck events, offset/frequency instability |
| `get_port_status` | Get port states and transitions | Debugging port issues, tracking state changes |
| `get_gnss_status` | Get GNSS receiver status | Checking GNSS fix quality, signal issues on grandmasters |
| `analyze_holdover` | Track holdover events and duration | Investigating holdover behavior, checking recovery |
| `analyze_frequency_drift` | Analyze frequency adjustments | Detecting oscillator issues, tracking drift rates |
| `run_pmc_query` | Execute PMC commands | Getting real-time data (PARENT_DATA_SET, etc.) |
| `analyze_sync_status` | Analyze sync status with optional path delay | Use `include_path_delay=True` for delay/asymmetry analysis |

### Targeting Different OpenShift Clusters

By default, the PTP MCP tools use the default kubeconfig (the cluster you're currently logged into). To query a different OpenShift cluster, you must provide a **base64-encoded** kubeconfig.

**IMPORTANT: The kubeconfig MUST be base64 encoded before passing to MCP tools.**

**How to target a specific cluster:**

1. **Base64 encode the kubeconfig file** - The kubeconfig content must be base64 encoded first:
   ```bash
   cat /path/to/kubeconfig.yaml | base64 -w0
   ```
   This produces a single-line base64 string with no line breaks.

2. **Pass the base64 string to the MCP tool** - Use the resulting base64 string as the `kubeconfig` parameter value

**Example workflow:**

When the user provides or attaches a kubeconfig file and asks to target a specific cluster:
1. First, base64 encode the kubeconfig content: `cat kubeconfig | base64 -w0`
2. Then pass the base64 string to the PTP MCP tool's `kubeconfig` parameter

**Example user requests:**
- "Check PTP status on cluster vcl03" (user attaches kubeconfig file)
- "Here's my kubeconfig for the production cluster, can you check the grandmaster status?"

For these requests, you must:
1. Take the kubeconfig file content
2. Base64 encode it (conceptually: `base64 -w0`)
3. Pass the encoded string to the `kubeconfig` parameter of the MCP tool

**Important notes:**
- If no kubeconfig is provided, the tools use the default cluster
- The kubeconfig parameter expects a **base64-encoded string**, not raw file content
- The kubeconfig is used only for that specific tool call - each request can target a different cluster
- Kubeconfig files typically contain sensitive credentials - they are written to a temporary file with restricted permissions and deleted immediately after use

---

## Part 1: Operator Quick Start

### Decision Tree: Is PTP Working?

```
START: Is the linuxptp-daemon pod running?
  |
  +-- NO --> Check pod status:
  |          $ oc get pods -n openshift-ptp
  |          Look for: CrashLoopBackOff, ImagePullBackOff, Pending, Error
  |          See: "Pod Status Issues" in Common Failure Modes
  |
  +-- YES --> Is the servo locked (s2 state)?
               |
               +-- NO --> Check logs for servo state:
               |          $ oc logs ds/linuxptp-daemon -c linuxptp-daemon-container -n openshift-ptp | grep "s[0-2] freq"
               |          s0 = unlocked, s1 = step, s2 = locked
               |          See: "Servo Instability" in Common Failure Modes
               |
               +-- YES --> Is offset within threshold (typically ±100ns)?
                            |
                            +-- NO --> Check for clockcheck events:
                            |          $ oc logs ... | grep "clockcheck"
                            |          Check grandmaster stability
                            |          See: "Offset Threshold Exceeded"
                            |
                            +-- YES --> PTP is HEALTHY
```

### Common Issues at a Glance

| Symptom | Likely Cause | Quick Fix | MCP Tool |
|---------|--------------|-----------|----------|
| Pod CrashLoopBackOff | Invalid ptpconfig | Check ptpconfig YAML syntax | `get_ptp_config` |
| "s0" in logs continuously | No sync messages received | Check network connectivity, grandmaster | `analyze_sync_status` |
| Large offset (>1us) | Servo instability or GM issues | Check clockcheck events, GM status | `analyze_servo_stability` |
| "clockcheck: clock frequency changed" | System interference | Check for multiple daemons, power mgmt | `analyze_servo_stability` |
| Clock class 248 or 255 | No valid time source | Check GNSS/upstream GM | `get_grandmaster_status` |

**Quick Diagnosis with MCP Tools:**

For rapid triage, use `check_ptp_health` to get an overall health assessment covering configuration, synchronization, and log analysis.

### Emergency Recovery Procedures

**Complete PTP Failure:**
```bash
# 1. Check operator and daemon status
oc get pods -n openshift-ptp

# 2. Check for configuration errors
oc get ptpconfig -n openshift-ptp -o yaml

# 3. Check daemon logs for errors
oc logs ds/linuxptp-daemon -c linuxptp-daemon-container -n openshift-ptp --tail=100

# 4. If needed, restart the daemon
oc delete pod -l app=linuxptp-daemon -n openshift-ptp
```

---

## Part 2: Understanding PTP in OpenShift

### Architecture Overview

The OpenShift PTP Operator deploys and manages linuxptp components:

```
+-------------------+     +-------------------+     +-------------------+
|   Grandmaster     |---->|  Boundary Clock   |---->|  Ordinary Clock   |
|   (T-GM)          |     |  (T-BC)           |     |  (T-OC/Slave)     |
| - GNSS receiver   |     | - ptp4l (master)  |     | - ptp4l (slave)   |
| - ts2phc          |     | - ptp4l (slave)   |     | - phc2sys         |
| - ptp4l           |     | - phc2sys         |     +-------------------+
+-------------------+     +-------------------+
```

**Key Components:**
- **ptp4l**: PTP daemon implementing IEEE 1588
- **phc2sys**: Synchronizes system clock to PHC (PTP Hardware Clock)
- **ts2phc**: Synchronizes PHC to external timestamps (GNSS 1PPS)
- **linuxptp-daemon**: OpenShift wrapper managing all components

### Clock Types Explained

| Type | Abbreviation | Role | Configuration |
|------|--------------|------|---------------|
| Ordinary Clock | OC | Single-port slave or master | `clock_type OC` |
| Boundary Clock | BC | Multi-port, terminates PTP | `clock_type BC` |
| Transparent Clock | TC | Passes PTP messages, adds residence time | `clock_type TC` |
| Grandmaster | GM/T-GM | Primary time source (usually GNSS) | `clock_type OC` + GNSS |

### ITU-T G.8275.x Profile Overview

**G.8275.1 (Full Timing Support - FTS):**
- Layer 2 transport (Ethernet)
- Domains 24-43
- Max time error: ±1.5 microseconds
- Used for: Mobile fronthaul, critical timing

**G.8275.2 (Partial Timing Support - PTS):**
- Layer 3 transport (IP/UDP)
- Unicast or multicast
- Max time error: ±5 microseconds
- Used for: Packet networks without full PTP support

**Key Configuration for G.8275.x:**
```
domainNumber 24          # Domain 24-43 for telecom
dataset_comparison G.8275.x
G.8275.defaultDS.localPriority 128
G.8275.portDS.localPriority 128
```

### OpenShift PTP Operator Components

> **Official Documentation:** For complete PtpConfig CRD reference and configuration examples, see [Red Hat OpenShift PTP Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/networking/using-ptp-hardware).

**Key PtpConfig Fields:**

| Field | Purpose |
|-------|---------|
| `profile[].ptp4lOpts` | Command-line options for ptp4l (e.g., "-2 -s") |
| `profile[].phc2sysOpts` | Options for phc2sys (e.g., "-a -r -n 24") |
| `profile[].ptp4lConf` | Full ptp4l configuration content |
| `profile[].plugins` | Hardware-specific plugins (e.g., E810) |
| `ptpClockThreshold` | Offset/holdover thresholds for events |
| `recommend[].match` | Node selection via labels or names |

### PTP Events Framework

The PTP Operator can publish events via the cloud-events framework when `enableEventPublisher: true` is set in the PtpOperatorConfig.

**Event Types:**

| Event | States | Description |
|-------|--------|-------------|
| `lock-state` | LOCKED, HOLDOVER, FREERUN | PTP equipment lock state |
| `os-clock-sync-state` | LOCKED, FREERUN | System clock sync state |
| `gnss-sync-status` | LOCKED, FREERUN | GNSS clock signal sync state |
| `ptp-clock-class-change` | Class values (6, 7, 135, etc.) | Clock class transitions |

**Threshold Configuration:**
```yaml
ptpClockThreshold:
  holdOverTimeout: 5        # Seconds before FREERUN state
  maxOffsetThreshold: 100   # Nanoseconds (positive limit)
  minOffsetThreshold: -100  # Nanoseconds (negative limit)
```

> **MCP Tools:** Use `check_ptp_health` to monitor these states. The tool checks sync status and reports when thresholds are exceeded.

---

## Part 3: Diagnostic Procedures

> **Using MCP Tools:** Instead of running manual commands, use the MCP tools for automated diagnostics:
> - `check_ptp_health` - Performs Steps 1-4 automatically and returns overall health status
> - `query_ptp` - Ask questions in natural language like "Is PTP healthy?" or "What is the current offset?"

### Step 1: Check Pod Status

```bash
# List all PTP pods
oc get pods -n openshift-ptp

# Expected output for healthy system:
# NAME                            READY   STATUS    RESTARTS   AGE
# linuxptp-daemon-xxxxx           3/3     Running   0          1h
# ptp-operator-xxxxx              1/1     Running   0          1h
```

**Pod Status Meanings:**
- `Running 3/3`: All containers healthy
- `Running 2/3`: One container failed (check logs)
- `CrashLoopBackOff`: Configuration or runtime error
- `Pending`: Scheduling issues or resource constraints

### Step 2: Verify Configuration

> **MCP Tool:** Use `get_ptp_config` to retrieve and validate configuration. It automatically validates syntax and checks ITU-T G.8275.1 compliance.

```bash
# Get current PTP configuration
oc get ptpconfig -n openshift-ptp -o yaml

# Validate key settings:
# - domainNumber matches network
# - interface exists on node
# - slaveOnly/masterOnly appropriate for role
# - clock_type matches deployment
```

**Common Configuration Errors:**
- Wrong interface name
- Domain number mismatch
- Missing required ptp4l options
- Invalid ptp4lConf syntax

### Step 3: Analyze Logs

> **MCP Tools:**
> - `get_ptp_logs` - Fetches logs and extracts structured data (grandmaster info, sync status, clock hierarchy)
> - `search_logs` - Search for specific patterns with optional time range and log level filters

```bash
# Get recent logs
oc logs ds/linuxptp-daemon -c linuxptp-daemon-container -n openshift-ptp --tail=500

# Filter for specific components
oc logs ... | grep "ptp4l\["      # PTP daemon messages
oc logs ... | grep "phc2sys\["    # System clock sync
oc logs ... | grep "ts2phc\["     # GNSS sync (grandmaster)
oc logs ... | grep "dpll\["       # DPLL status
oc logs ... | grep "gnss\["       # GNSS receiver status

# Look for errors
oc logs ... | grep -iE "(error|warning|fault|failed)"
```

### Step 4: Check Synchronization Status

> **MCP Tools:**
> - `analyze_sync_status` - Analyzes sync status including servo state, offsets, and BMCA role
> - `analyze_servo_stability` - Deep analysis of servo behavior, clockcheck events, and stability metrics

**Servo State (ptp4l and phc2sys logs):**
```
ptp4l[xxx]: [ens1f0] master offset -5 s2 freq +1234 path delay 456
phc2sys[xxx]: CLOCK_REALTIME phc offset 5 s2 freq -89900 delay 500
                                          ^^
                                          Servo state: s0=unlocked, s1=step, s2=locked
```

**Offset Values:**
- `offset 5`: 5 nanoseconds offset (excellent)
- `offset 500`: 500 nanoseconds (good)
- `offset 5000`: 5 microseconds (concerning)
- `offset 50000`: 50 microseconds (problem)

**Frequency Values:**
- `freq -89900`: Frequency adjustment in ppb (parts per billion)
- Stable values indicate good sync
- Large changes indicate instability

### Step 5: Validate Grandmaster

> **MCP Tools:**
> - `get_grandmaster_status` - Get GM identity, clock class, and BMCA state from logs
> - `run_pmc_query` - Execute PMC commands (PARENT_DATA_SET, CURRENT_DATA_SET, etc.) for real-time data
> - `get_clock_hierarchy` - Understand the full clock hierarchy and port relationships

```bash
# Check grandmaster via PMC
oc exec -n openshift-ptp $(oc get pods -n openshift-ptp -l app=linuxptp-daemon -o name | head -1) -- \
  pmc -u -b 0 -f /var/run/ptp4l.0.config "GET PARENT_DATA_SET"

# Expected output includes:
# grandmasterIdentity     507c6f.fffe.1fb16c
# gm.ClockClass           6              # 6 = GNSS locked
# grandmasterPriority1    128
# grandmasterPriority2    128
```

**Clock Class Interpretation (ITU-T G.8275.1):**
- Class 6: T-GM locked to PRTC (e.g. GNSS)
- Class 7: T-GM holdover, within holdover specification
- Class 135: T-BC holdover, within holdover specification
- Class 140: T-GM holdover, out of spec, traceable to PRC/PRS
- Class 150: T-GM holdover, out of spec, traceable to SSU-A/ST2
- Class 160: T-GM holdover, out of spec, Category 3 frequency reference
- Class 165: T-BC holdover, out of holdover specification
- Class 248: Free-running, no valid time reference
- Class 255: Slave-only clock (T-TSC), does not act as master

---

## Part 4: Log Pattern Reference

### ptp4l Log Patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| Port state change | `port 1: LISTENING to SLAVE` | Normal state transition |
| Master selected | `selected best master clock` | BMCA completed |
| Announce timeout | `announce timeout` | No announcements from master |
| Fault detected | `port 1: FAULTY` | Port error condition |

**Port State Machine:**
```
INITIALIZING -> LISTENING -> (SLAVE or MASTER or PASSIVE)
                    |
                    v
              UNCALIBRATED (temporary during sync)
```

### phc2sys Log Patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| Normal sync | `offset 5 s2 freq -89900` | Locked, good offset |
| Unlocked | `offset 5000 s0` | Not synchronized |
| Step | `offset 5 s1` | Large correction applied |
| Clockcheck | `clockcheck: clock frequency changed unexpectedly` | Servo reset |

**Servo States:**
- `s0`: Unlocked - not tracking, large offset
- `s1`: Step - applying large correction
- `s2`: Locked - tracking with small corrections

### ts2phc Log Patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| NMEA received | `nmea sentence: GPRMC` | GPS data received |
| NMEA delay | `nmea delay: 125000 ns` | 1PPS to message latency |
| PHC offset | `master offset 5 s2` | PHC synchronized |

### DPLL Log Patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| Locked | `Status 3, In spec true` | DPLL locked to reference |
| Holdover | `On holdover true` | Using stored frequency |
| Source loss | `Source GNSS lost true` | GNSS reference lost |

**DPLL Status Codes:**
- 0: Invalid
- 1: Initializing
- 2: Freerun
- 3: Locked
- 4: Locked with holdover capability
- 5: Holdover

### GNSS Log Patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| Status | `gnss[xxx]: status 3` | GNSS fix status |
| Offset | `gnss[xxx]: offset 50` | GNSS time offset |

**GNSS Status Codes:**
- 0: No fix
- 1: 2D fix
- 2: 3D fix
- 3: 3D fix with holdover capability

### PMC Output Interpretation

**PARENT_DATA_SET:**
```
grandmasterIdentity     507c6f.fffe.1fb16c    # GM clock ID
gm.ClockClass           6                      # Quality level
gm.ClockAccuracy        0x21                   # 100ns accuracy
grandmasterPriority1    128                    # BMCA priority
grandmasterPriority2    64                     # Tiebreaker priority
parentPortIdentity      b4e9b8.ffff.d9cfe0-3   # Parent port
```

**Clock Accuracy Values (0x21, etc.):**
- 0x20: 25ns
- 0x21: 100ns
- 0x22: 250ns
- 0x23: 1us
- 0x24: 2.5us
- 0xFE: Unknown

---

## Part 5: Metric Thresholds

### Offset Thresholds by Profile

| Profile | Max Offset | Warning Threshold | Action Threshold |
|---------|------------|-------------------|------------------|
| G.8275.1 (FTS) | ±1.5 us | ±1.0 us | ±1.2 us |
| G.8275.2 (PTS) | ±5 us | ±3 us | ±4 us |
| Default OpenShift | ±100 ns | ±50 ns | ±80 ns |
| Lab/Testing | ±1 us | ±500 ns | ±800 ns |

**ptpconfig Threshold Settings:**
```yaml
ptpClockThreshold:
  holdOverTimeout: 5        # Seconds before declaring holdover
  maxOffsetThreshold: 100   # Nanoseconds, positive limit
  minOffsetThreshold: -100  # Nanoseconds, negative limit
```

### Clock Class Values and Meanings (ITU-T G.8275.1)

| Class | Clock Type | Meaning | Action |
|-------|------------|---------|--------|
| 6 | T-GM | Locked to PRTC (e.g. GNSS) | Normal operation |
| 7 | T-GM | Holdover, within holdover specification | Monitor, will recover |
| 135 | T-BC | Holdover, within holdover specification | Monitor, will recover |
| 140 | T-GM | Holdover, out of spec, traceable to PRC/PRS | Warning, check reference |
| 150 | T-GM | Holdover, out of spec, traceable to SSU-A/ST2 | Warning, check reference |
| 160 | T-GM | Holdover, out of spec, Category 3 freq ref | Action needed |
| 165 | T-BC | Holdover, out of holdover specification | Action needed |
| 248 | T-GM/T-BC | Free-running, no valid time reference | Critical |
| 255 | T-TSC | Slave-only, does not act as master | Normal for slave nodes |

### Frequency Adjustment Limits

| Condition | Frequency Value | Interpretation |
|-----------|-----------------|----------------|
| Normal | ±100,000 ppb | Typical hardware variation |
| Stable | <1,000 ppb/hour change | Good oscillator |
| Concerning | >10,000 ppb/hour change | Check temperature, hardware |
| Critical | >100,000 ppb change | Hardware issue or interference |

### DPLL State Codes

| State | Code | Description | Expected Duration |
|-------|------|-------------|-------------------|
| Invalid | 0 | Not initialized | Startup only |
| Initializing | 1 | Starting up | Seconds |
| Freerun | 2 | No lock, using nominal frequency | Investigate if >1min |
| Locked | 3 | Locked to reference | Normal operation |
| Locked-HO | 4 | Locked with holdover capability | Normal operation |
| Holdover | 5 | Using stored frequency | Minutes to hours |

---

## Part 6: Common Failure Modes

> **Quick Diagnosis:** Use `check_ptp_health` to automatically detect which failure mode applies and get targeted recommendations.

### Grandmaster Loss

> **MCP Tools:** Use `get_grandmaster_status` to check GM identity and clock class. Use `search_logs` with query "announce timeout" to find timeout events.

**Symptoms:**
- Clock class changes from 6 to 7, then higher
- `announce timeout` messages in ptp4l logs
- Offset values increasing over time

**Diagnosis:**
```bash
# Check GM status
oc logs ds/linuxptp-daemon -c linuxptp-daemon-container -n openshift-ptp | grep -E "(gm\.|grandmaster|GM\[)"

# Check for announce timeouts
oc logs ... | grep "announce timeout"

# Verify network connectivity to GM
```

**Resolution:**
1. Verify grandmaster is operational
2. Check network path to grandmaster
3. Verify domain number matches
4. Check for firewall blocking PTP (UDP 319, 320)

### Clock Class Degradation

> **MCP Tools:** Use `get_grandmaster_status` to track clock class. Use `get_gnss_status` to check GNSS receiver status and `analyze_holdover` to monitor holdover state.

**Symptoms:**
- Clock class value increasing (T-GM: 6 -> 7 -> 140/150/160 -> 248, T-BC: 135 -> 165 -> 248)
- DPLL entering holdover mode
- GNSS source loss messages

**Diagnosis:**
```bash
# Track clock class changes
oc logs ... | grep -i "clockclass\|clock.class"

# Check GNSS status
oc logs ... | grep "gnss\["

# Check DPLL status
oc logs ... | grep "dpll\["
```

**Resolution:**
1. Check GNSS antenna connection
2. Verify GNSS receiver has sky visibility
3. Check for RF interference
4. Monitor holdover timeout settings

### Holdover Events

> **MCP Tools:** Use `analyze_holdover` to track holdover events, duration, and clock class during holdover. Use `analyze_frequency_drift` to monitor frequency stability during holdover.

**Symptoms:**
- `On holdover true` in DPLL logs
- Clock class transitions
- Frequency values drifting

**Diagnosis:**
```bash
# Check holdover entry
oc logs ... | grep -i holdover

# Monitor frequency drift
oc logs ... | grep "freq" | tail -50
```

**Understanding Holdover:**
- Holdover uses stored frequency from when DPLL was locked
- Accuracy degrades over time based on oscillator quality
- OCXO: Hours of accurate holdover
- TCXO: Minutes of accurate holdover

**Resolution:**
1. Restore primary reference (GNSS, upstream GM)
2. Monitor holdover duration
3. Plan for holdover timeout if extended

### GNSS Signal Loss

> **MCP Tools:** Use `get_gnss_status` to check GNSS fix quality, signal status, and receiver health. This tool parses gnss and ts2phc log entries automatically.

**Symptoms:**
- `Source GNSS lost true` in logs
- Clock class changing from 6
- ts2phc errors or no output

**Diagnosis:**
```bash
# Check GNSS status
oc logs ... | grep "gnss\["

# Check ts2phc logs
oc logs ... | grep "ts2phc\["

# Check for NMEA sentences
oc logs ... | grep -i nmea
```

**Resolution:**
1. Check physical antenna connection
2. Verify antenna has clear sky view
3. Check for RF interference (LTE, radar)
4. Verify GNSS receiver power and configuration

### Servo Instability ("clockcheck" events)

> **MCP Tools:** Use `analyze_servo_stability` to automatically detect clockcheck events, analyze servo state, and get offset/frequency statistics with stability assessment and recommendations.

**Symptoms:**
- `clockcheck: clock frequency changed unexpectedly` messages
- Offset spikes (e.g., normal 5ns suddenly jumps to 500ns)
- Frequency values showing sudden changes

**Example Log Sequence:**
```
phc2sys: CLOCK_REALTIME phc offset 11 s2 freq -89878 delay 506
phc2sys: clockcheck: clock frequency changed unexpectedly!
phc2sys: CLOCK_REALTIME phc offset -481 s2 freq -90366 delay 506
phc2sys: CLOCK_REALTIME phc offset -456 s2 freq -90486 delay 509
... (recovery over several seconds)
phc2sys: CLOCK_REALTIME phc offset 5 s2 freq -89900 delay 500
```

**Causes:**
1. Multiple ptp4l/phc2sys instances modifying same clock
2. System resume from suspend/sleep
3. Power management (C-states) interrupting timing
4. Large PHC step corrections
5. Feedback loop between ptp4l and phc2sys on same clock

**Diagnosis:**
```bash
# Check for multiple daemon instances
oc exec -n openshift-ptp <pod> -- pgrep -a ptp4l
oc exec -n openshift-ptp <pod> -- pgrep -a phc2sys

# Check clockcheck event frequency
oc logs ... | grep clockcheck | wc -l

# Review servo configuration
oc get ptpconfig -n openshift-ptp -o yaml | grep -A5 "step_threshold"
```

**Resolution:**
1. Ensure single daemon per interface
2. Use separate config files for ptp4l and phc2sys
3. Adjust step_threshold if needed:
   ```
   step_threshold 2.0       # Default: 0 (disabled)
   first_step_threshold 0.00002
   ```
4. Disable aggressive power management
5. Consider using SCHED_FIFO for daemon priority

### Port State Issues

> **MCP Tools:** Use `get_port_status` to get current port states and transition history. Use `analyze_sync_status` with `include_path_delay=True` to check path delay characteristics and detect asymmetry issues.

**Symptoms:**
- Port stuck in LISTENING state
- Repeated SLAVE to UNCALIBRATED transitions
- Port in FAULTY state

**Diagnosis:**
```bash
# Check port state transitions
oc logs ... | grep "port [0-9]:"

# Check for specific port issues
oc logs ... | grep -i fault
```

**Port States:**
- `LISTENING`: Waiting for announce messages
- `UNCALIBRATED`: Syncing, not yet stable
- `SLAVE`: Successfully synchronized
- `MASTER`: Acting as master clock
- `PASSIVE`: Backup, not forwarding time
- `FAULTY`: Error condition

**Resolution:**
1. Check network connectivity on interface
2. Verify VLAN and network configuration
3. Check for cable/SFP issues
4. Verify announce messages are being received

### Intel E810 NIC Issues

> **MCP Tools:** Use `get_gnss_status` for GNSS receiver issues, `get_ptp_config` to verify plugin configuration, and `check_ptp_health` for full analysis.

The Intel E810 Westport Channel NIC requires special plugin configuration in OpenShift PTP.

**Common E810 Issues:**

| Symptom | Cause | Resolution |
|---------|-------|------------|
| ts2phc not starting | Missing E810 plugin config | Add `plugins.e810` section to PtpConfig |
| GNSS not locking | Antenna/cable issue | Check physical connection, verify sky visibility |
| 1PPS signal missing | ts2phc misconfiguration | Verify `ts2phcOpts` and `ts2phcConf` settings |
| SyncE not working | Missing synce4l config | Configure `synce4lOpts` and `synce4lConf` in plugin |
| Clock class stuck at 248 | GNSS not providing fix | Check `gnss[` logs for fix status |

**E810 Plugin Configuration:**
```yaml
plugins:
  e810:
    enableDefaultConfig: true
    ts2phcOpts: "-m"
    ts2phcConf: |
      [nmea]
      ts2phc.master 1
      [global]
      use_syslog 0
      ts2phc.pulsewidth 100000000
```

**Diagnosing E810 GNSS Issues:**
```bash
# Check ts2phc logs for GNSS
oc logs ds/linuxptp-daemon -c linuxptp-daemon-container -n openshift-ptp | grep "ts2phc\["

# Check for NMEA sentences
oc logs ... | grep -i nmea

# Check GNSS status
oc logs ... | grep "gnss\["
```

**E810-Specific Log Patterns:**

| Pattern | Meaning |
|---------|---------|
| `ts2phc[]: nmea delay: 125000 ns` | Normal NMEA processing latency |
| `ts2phc[]: master offset 0 s2` | ts2phc locked to GNSS 1PPS |
| `gnss[]: status 3` | GNSS has 3D fix with holdover capability |
| `gnss[]: status 0` | No GNSS fix - check antenna |
| `dpll[]: Source GNSS lost true` | GNSS signal lost, entering holdover |

---

## Part 7: Deep Technical Reference

### BMCA Algorithm Details

**Best Master Clock Algorithm (BMCA)** determines which clock becomes grandmaster:

**Comparison Order:**
1. Priority1 (lower wins)
2. Clock Class (lower wins)
3. Clock Accuracy (lower wins)
4. Offset Scaled Log Variance (lower wins)
5. Priority2 (lower wins)
6. Clock Identity (lower wins - tiebreaker)

**G.8275.x Alternate BMCA:**
- Uses local priority in addition to standard fields
- `G.8275.defaultDS.localPriority`: Node-level priority
- `G.8275.portDS.localPriority`: Port-level priority

### Servo Controller Tuning

**PI Controller Parameters:**
```
pi_proportional_const 0.0    # Use scale/exponent instead
pi_integral_const 0.0
pi_proportional_scale 0.0
pi_proportional_exponent -0.3
pi_proportional_norm_max 0.7
pi_integral_scale 0.0
pi_integral_exponent 0.4
pi_integral_norm_max 0.3
```

**Key Settings:**
- `step_threshold`: Offset requiring step correction (0=disabled)
- `first_step_threshold`: Threshold for first correction
- `max_frequency`: Maximum frequency adjustment (ppb)
- `sanity_freq_limit`: Frequency change limit per interval

**Tuning Guidelines:**
- Higher proportional gain: Faster response, more overshoot
- Higher integral gain: Better steady-state, slower convergence
- For stable networks: Use defaults
- For noisy networks: Reduce gains, increase filter length

### DPLL State Machine

```
                    +-------------+
                    | INITIALIZING|
                    +------+------+
                           |
              +------------+------------+
              |                         |
              v                         v
       +------+------+           +------+------+
       |   FREERUN   |           |   LOCKED    |
       +------+------+           +------+------+
              |                         |
              |    Reference lost       | Reference lost
              +------------+------------+
                           |
                           v
                    +------+------+
                    |  HOLDOVER   |
                    +------+------+
                           |
                           | Timeout or reference restored
                           v
                    +------+------+
                    |   FREERUN   | (or back to LOCKED)
                    +-------------+
```

### ITU-T Compliance Validation

**G.8275.1 Requirements Checklist:**
- [ ] Domain number 24-43
- [ ] Layer 2 transport (network_transport L2)
- [ ] Multicast addressing (01:1B:19:00:00:00)
- [ ] Clock class appropriate for role
- [ ] Announce interval: -3 (8/second)
- [ ] Sync interval: -4 (16/second)
- [ ] Delay request interval: -4 (16/second)

**Validation Command:**
```bash
oc get ptpconfig -n openshift-ptp -o yaml | grep -E "domainNumber|network_transport|logAnnounceInterval|logSyncInterval"
```

### SyncE Integration

**Synchronous Ethernet (SyncE)** provides physical layer frequency synchronization:

**Benefits with PTP:**
- Frequency from SyncE, phase from PTP
- Better holdover performance
- Reduced PTP message sensitivity

**Checking SyncE Status:**
```bash
# Check for SyncE support (if available)
oc exec -n openshift-ptp <pod> -- ls /sys/class/net/*/device/synce/
```

---

## Appendix A: Quick Reference Commands

```bash
# Pod status
oc get pods -n openshift-ptp

# Configuration
oc get ptpconfig -n openshift-ptp -o yaml

# Recent logs
oc logs ds/linuxptp-daemon -c linuxptp-daemon-container -n openshift-ptp --tail=500

# Filter logs by component
oc logs ... | grep "ptp4l\["
oc logs ... | grep "phc2sys\["
oc logs ... | grep "ts2phc\["
oc logs ... | grep "dpll\["
oc logs ... | grep "gnss\["

# Search for errors
oc logs ... | grep -iE "(error|warning|fault|clockcheck)"

# PMC queries
oc exec -n openshift-ptp <pod> -- pmc -u -b 0 -f /var/run/ptp4l.0.config "GET PARENT_DATA_SET"
oc exec -n openshift-ptp <pod> -- pmc -u -b 0 -f /var/run/ptp4l.0.config "GET CURRENT_DATA_SET"
oc exec -n openshift-ptp <pod> -- pmc -u -b 0 -f /var/run/ptp4l.0.config "GET TIME_PROPERTIES_DATA_SET"
```

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| BMCA | Best Master Clock Algorithm - determines clock hierarchy |
| BC | Boundary Clock - multi-port clock that terminates PTP |
| DPLL | Digital Phase-Locked Loop - hardware frequency tracking |
| GM | Grandmaster - primary time source in PTP domain |
| GNSS | Global Navigation Satellite System (GPS, Galileo, etc.) |
| OC | Ordinary Clock - single-port PTP clock |
| PHC | PTP Hardware Clock - NIC's hardware timestamp clock |
| PMC | PTP Management Client - tool for querying PTP status |
| ppb | Parts per billion - frequency offset unit |
| PRTC | Primary Reference Time Clock - highest quality clock |
| SyncE | Synchronous Ethernet - physical layer timing |
| TC | Transparent Clock - passes PTP, adds residence time |

---

## Appendix C: MCP Tool Quick Reference

### Which MCP Tool Should I Use?

| Question / Task | Recommended MCP Tool |
|-----------------|---------------------|
| "Is PTP working?" | `check_ptp_health` |
| "What's wrong with PTP?" | `check_ptp_health` |
| "Show me the PTP configuration" | `get_ptp_config` |
| "What is the current grandmaster?" | `get_grandmaster_status` |
| "Is the servo locked?" | `analyze_sync_status` |
| "Show me recent PTP logs" | `get_ptp_logs` |
| "Search for errors in logs" | `search_logs` |
| "What is the clock hierarchy?" | `get_clock_hierarchy` |
| "Are there clockcheck events?" | `analyze_servo_stability` |
| "What are the port states?" | `get_port_status` |
| "Is GNSS working?" | `get_gnss_status` |
| "Is the system in holdover?" | `analyze_holdover` |
| "Is frequency drifting?" | `analyze_frequency_drift` |
| "Get real-time clock data" | `run_pmc_query` |
| "Check network path timing" | `analyze_sync_status` (with `include_path_delay=True`) |
| Any question in plain English | `query_ptp` |

### MCP Tool Parameters

**Common Parameters (most tools):**
- `namespace`: OpenShift namespace (default: "openshift-ptp")
- `lines`: Number of log lines to analyze (default: 1000)

**Tool-Specific Parameters:**

| Tool | Key Parameters |
|------|----------------|
| `get_ptp_config` | `namespace` |
| `get_ptp_logs` | `namespace`, `lines`, `since` |
| `search_logs` | `query`, `time_range`, `log_level` |
| `get_grandmaster_status` | `detailed` (boolean) |
| `analyze_sync_status` | `include_offsets`, `include_bmca`, `include_path_delay` |
| `get_clock_hierarchy` | `include_ports`, `include_priorities` |
| `check_ptp_health` | `check_config`, `check_sync`, `check_logs` |
| `query_ptp` | `question`, `context` |
| `analyze_servo_stability` | `namespace`, `lines` |
| `get_port_status` | `interface`, `include_history` |
| `get_gnss_status` | `namespace`, `lines` |
| `analyze_holdover` | `namespace`, `lines` |
| `analyze_frequency_drift` | `window_minutes` |
| `run_pmc_query` | `command` (PARENT_DATA_SET, CURRENT_DATA_SET, etc.) |

### Troubleshooting Workflows

**Quick Health Check:**
1. Run `check_ptp_health` for overall status
2. If unhealthy, review the checks output for configuration, sync, and log issues
3. Follow up with specific tools based on the failing check

**Investigating Sync Issues:**
1. Run `analyze_sync_status` to check lock state and offsets
2. Run `analyze_servo_stability` to check for clockcheck events
3. Run `get_grandmaster_status` to verify GM is stable

**GNSS/Grandmaster Issues:**
1. Run `get_gnss_status` to check receiver status
2. Run `analyze_holdover` to see if system entered holdover
3. Run `run_pmc_query` with "PARENT_DATA_SET" for real-time GM info

**Network/Port Issues:**
1. Run `get_port_status` to see current states and transitions
2. Run `analyze_sync_status` with `include_path_delay=True` to check path delays
3. Run `search_logs` with query "FAULTY" to find port errors

---
