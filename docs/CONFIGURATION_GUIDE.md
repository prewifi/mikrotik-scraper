# Configuration Guide

This document explains how to configure the Mikrotik Network Inventory system through the YAML configuration file.

## Available Configuration Files

1. **`test-config.yaml`** - Basic test configuration
2. **`config-ubiquiti.yaml`** - Optimized configuration for infrastructures with external Ubiquiti devices

## Configuration File Structure

### 1. Logging Section

```yaml
logging:
  level: INFO           # Log level: DEBUG, INFO, WARNING, ERROR
  file: null            # null = console only, or path to log file
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 2. Routers Section

Define the routers to query:

```yaml
routers:
  - name: "Router Name"    # Descriptive name (optional)
    ip: "10.200.32.2"      # Router IP address
    username: "admin"      # RouterOS username
    password: "password"   # RouterOS password
    port: 8728            # API RouterOS port (default: 8728)
    timeout: 10           # Connection timeout in seconds
```

You can add multiple routers by simply repeating the block:

```yaml
routers:
  - name: "Router 1"
    ip: "10.200.32.2"
    username: "admin"
    password: "pass1"
  
  - name: "Router 2"
    ip: "10.200.32.3"
    username: "admin"
    password: "pass2"
```

### 3. Collection Section

Control **what** to collect and **how**:

```yaml
collection:
  # Collection mode
  parallel: true         # true = parallel (faster), false = sequential
  max_workers: 5        # Maximum number of parallel workers
  retry_attempts: 3     # Number of retry attempts on error
  retry_delay: 2        # Delay between retries (seconds)
  
  # What to collect
  collect:
    system_info: true      # System info (CPU, RAM, RouterOS version)
    interfaces: true       # Network interfaces list
    ip_addresses: true     # Configured IP addresses
    neighbors: true        # IP neighbors (LLDP/CDP)
    pppoe_active: true     # Active PPPoE sessions
    pppoe_secrets: true    # Configured PPPoE users
    wireless: false        # Wireless interface details
```

#### When to Disable Wireless?

Disable `wireless: false` when:
- You use external wireless devices (e.g., Ubiquiti AirMax, AirFiber)
- Wireless links are not directly on the Mikrotik RouterBoard
- You want to reduce data collection time

Ubiquiti devices will still be visible via `neighbors: true`.

### 4. Analysis Section

Control **how** to analyze the collected data:

```yaml
analysis:
  enabled: true           # Enable/disable complete analysis
  detect_anomalies: true  # Detect configuration anomalies
  analyze_links: false    # Analyze wireless link quality
  
  # Thresholds for anomaly detection
  min_link_quality: 60    # Minimum wireless link quality (%)
  max_cpu_load: 80        # Maximum CPU load (%)
  max_memory_usage: 90    # Maximum memory usage (%)
```

#### When to Disable analyze_links?

Disable `analyze_links: false` when:
- Wireless links are on external devices (Ubiquiti)
- You don't need link topology analysis
- You want to avoid warnings for unknown devices

**Note:** Even with `analyze_links: false`, configuration anomaly detection remains active if `detect_anomalies: true`.

### 5. Output Section

Control where and how to save files:

```yaml
output:
  directory: "inventory"   # Output directory
  
  formats:
    - json                 # JSON format (automation)
    - yaml                 # YAML format (readable)
  
  include_timestamp: true
  pretty_print: true
  summary_file: false      # true to generate text summary file
```

## Output File Naming

Files are saved with the pattern:

```
{Router_Hostname}_{YYYYMMDD}_{HHMMSS}.{format}
```

Examples:
```
RB_MARSICO_VETERE_20251016_073128.json
RB_MARSICO_VETERE_20251016_073128.yaml
```

Advantages:
- Immediate router identification
- Automatic chronological sorting
- Facilitates automation and batch processing

## Common Usage Scenarios

### Scenario 1: Infrastructure with External Ubiquiti Devices

**Situation:** Mikrotik router with wireless links managed by Ubiquiti antennas (AirMax, AirFiber).

**Recommended Configuration:**
```yaml
collection:
  collect:
    system_info: true
    interfaces: true
    ip_addresses: true
    neighbors: true       # ✓ Important to see Ubiquiti devices
    pppoe_active: true
    pppoe_secrets: true
    wireless: false       # ✗ Disabled because wireless is external

analysis:
  enabled: true
  analyze_links: false    # ✗ Disabled because links are external
  detect_anomalies: true  # ✓ Keep anomaly detection
```

### Scenario 2: Complete Collection with Analysis

**Situation:** You want to collect everything and analyze the complete topology.

**Recommended Configuration:**
```yaml
collection:
  collect:
    system_info: true
    interfaces: true
    ip_addresses: true
    neighbors: true
    pppoe_active: true
    pppoe_secrets: true
    wireless: true        # ✓ Enabled for complete analysis

analysis:
  enabled: true
  analyze_links: true     # ✓ Analyze link topology
  detect_anomalies: true  # ✓ Detect anomalies
```

### Scenario 3: Basic Inventory Only (Fast)

**Situation:** You only want a quick inventory without analysis.

**Recommended Configuration:**
```yaml
collection:
  collect:
    system_info: true
    interfaces: true
    ip_addresses: true
    neighbors: false
    pppoe_active: false
    pppoe_secrets: false
    wireless: false

analysis:
  enabled: false         # ✗ Completely disable analysis
```

## Execution

```bash
# With custom configuration file
python3 src/main.py -c config-ubiquiti.yaml -o /path/output

# With default configuration file (config.yaml)
python3 src/main.py -o /path/output

# JSON only
python3 src/main.py -c config-ubiquiti.yaml -o /path/output --json-only

# YAML only
python3 src/main.py -c config-ubiquiti.yaml -o /path/output --yaml-only
```

## Output Examples

### With analyze_links: false
```
Total Links: 0
Backbone Links: 0
PTP Links: 0
PTMP Links: 0
```

### With analyze_links: true
```
Total Links: 7
Backbone Links: 1
PTP Links: 3
PTMP Links: 2
PPPoE Connections: 1
```

## Troubleshooting

### Issue: "No routers were successfully queried"
- Verify router IP address is correct
- Verify username and password
- Verify API port (8728) is accessible
- Verify API is enabled on RouterOS

### Issue: "Too many warnings about unknown neighbors"
- Set `analyze_links: false` if neighbors are external devices

### Issue: "Output files too large"
- Disable unnecessary collection options
- Disable `wireless: false` if you don't use wireless interfaces on Mikrotik

### Issue: "Collection too slow"
- Enable `parallel: true`
- Increase `max_workers` (e.g., 10)
- Disable unnecessary collection options

## Best Practices

1. **Configuration Backup:** Keep different versions of configuration files for different scenarios
2. **Secure Credentials:** Don't commit files with real passwords to public repositories
3. **Incremental Testing:** First test with `analysis.enabled: false` to verify connectivity
4. **Output Directory:** Use different directories for test and production output
5. **Monitoring:** Enable `logging.file` to track executions in production

## References

- [CONFIGURATION_CHANGES.md](./CONFIGURATION_CHANGES.md) - Technical details of changes
- [AUTHENTICATION_FIX.md](./AUTHENTICATION_FIX.md) - Authentication troubleshooting
- [README.md](../README.md) - Main system documentation
