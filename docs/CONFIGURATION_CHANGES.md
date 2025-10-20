# System Configuration Changes

## Overview

The system has been modified to allow users to fully configure the behavior of data collection and analysis through the `test-config.yaml` configuration file.

## Implemented Changes

### 1. Configurable Data Collection

It is now possible to choose which data to collect from routers through the `collection.collect` section of the configuration file:

```yaml
collection:
  parallel: true
  max_workers: 5
  retry_attempts: 3
  retry_delay: 2
  
  # Data collection options - enable/disable specific data types
  collect:
    system_info: true      # System identity and resources
    interfaces: true       # Network interfaces
    ip_addresses: true     # IP addresses
    neighbors: true        # IP neighbors (LLDP/CDP)
    pppoe_active: true     # Active PPPoE sessions
    pppoe_secrets: true    # PPPoE secrets/users
    wireless: false        # Wireless interface details
```

**Available Options:**

- `system_info`: System information (identity, version, uptime, CPU, memory)
- `interfaces`: List of network interfaces
- `ip_addresses`: Configured IP addresses
- `neighbors`: IP neighbors (LLDP/CDP) - useful for identifying external Ubiquiti devices
- `pppoe_active`: Active PPPoE sessions
- `pppoe_secrets`: Configured PPPoE users
- `wireless`: Wireless interface details (disabled by default to avoid unnecessary queries when using external Ubiquiti devices)

**Advantages:**
- Reduces data collection time by eliminating unnecessary queries
- Reduces output file size
- Greater flexibility for specific scenarios

### 2. Disableable Link Quality Analysis

Wireless link quality analysis has been made optional, as it is unnecessary when using external Ubiquiti devices visible via IP Neighbors:

```yaml
analysis:
  enabled: true           # Enable/disable network analysis
  detect_anomalies: true  # Detect configuration issues
  analyze_links: false    # Disable link quality analysis (using external Ubiquiti devices)
  min_link_quality: 60    # Minimum wireless link quality (%) - ignored if analyze_links is false
  max_cpu_load: 80        # Maximum CPU load threshold (%)
  max_memory_usage: 90    # Maximum memory usage threshold (%)
```

**Available Options:**

- `enabled`: Enable/disable analysis completely (if disabled, only basic inventory is created)
- `analyze_links`: Enable/disable link quality analysis (backbone, PTP, PTMP)
- `detect_anomalies`: Enable/disable configuration anomaly detection

**Advantages:**
- Avoids unnecessary analysis when wireless links are managed by external devices
- Reduces warnings for devices not in the inventory
- Accelerates processing for large networks

### 3. New File Naming Pattern

Output files now follow the pattern: `{Hostname}_{YYYYMMDD}_{HHMMSS}`

**Before:**
```
inventory_20251015_151504.json
inventory_20251015_151504.yaml
```

**After:**
```
RB_MARSICO_VETERE_20251016_073128.json
RB_MARSICO_VETERE_20251016_073128.yaml
```

**Advantages:**
- Immediate router identification from filename
- Better organization when collecting data from multiple routers
- Facilitates automation and batch processing
- Standard pattern for chronological sorting

**Note:** Special characters in router name (spaces, slash) are replaced with underscore for filesystem compatibility.

## Modified Files

1. **`test-config.yaml`**
   - Added `collection.collect` section with data collection options
   - Added `analysis.analyze_links` option to disable link analysis
   - Added `analysis.enabled` option to disable complete analysis

2. **`src/mikrotik_client.py`**
   - Modified `collect_all_data()` to accept `collection_options`
   - Modified `get_interfaces()` to accept `include_wireless` parameter
   - Data collection now conditional based on options

3. **`src/main.py`**
   - Added `collection_options` parameter to `collect_router_data()`
   - Modified `collect_all_routers()` to read and pass collection options
   - Analysis now conditional based on `analysis.enabled`
   - Added `Optional` import from typing

4. **`src/analyzer.py`**
   - Modified `__init__()` to accept `config` parameter
   - Added handling for `analyze_links` and `detect_anomalies` options
   - `analyze()` method now skips link and anomaly analysis if disabled

5. **`src/inventory.py`**
   - Modified `save_json()` and `save_yaml()` to generate filename with pattern `{Hostname}_{YYYYMMDD}_{HHMMSS}`
   - Automatic handling of special characters in hostname

## Usage Examples

### Scenario 1: Complete Collection (Default)

```yaml
collection:
  collect:
    system_info: true
    interfaces: true
    ip_addresses: true
    neighbors: true
    pppoe_active: true
    pppoe_secrets: true
    wireless: true

analysis:
  enabled: true
  analyze_links: true
  detect_anomalies: true
```

### Scenario 2: Basic Inventory Only (No Analysis)

```yaml
collection:
  collect:
    system_info: true
    interfaces: true
    ip_addresses: true
    neighbors: true
    pppoe_active: false
    pppoe_secrets: false
    wireless: false

analysis:
  enabled: false
```

### Scenario 3: Inventory with External Ubiquiti Devices (Recommended)

```yaml
collection:
  collect:
    system_info: true
    interfaces: true
    ip_addresses: true
    neighbors: true        # Important to see Ubiquiti devices
    pppoe_active: true
    pppoe_secrets: true
    wireless: false        # Disabled because wireless is managed by Ubiquiti

analysis:
  enabled: true
  analyze_links: false     # Disabled because links are on external devices
  detect_anomalies: true   # Keep configuration anomaly detection
```

## Tests Performed

✅ Data collection with `wireless: false` - works correctly  
✅ Analysis with `analyze_links: false` - skips link analysis, 0 links identified  
✅ Output file with pattern `{Hostname}_{YYYYMMDD}_{HHMMSS}` - generated correctly  
✅ Complete system with recommended configuration - working  

## Backward Compatibility

All changes are backward compatible:

- If configuration options are not specified, the system uses default values (complete collection)
- Existing configuration files continue to work
- Client API is compatible with existing code

## Conclusion

The system now offers full configurability through `test-config.yaml`, allowing data collection to be optimized based on specific infrastructure (e.g., external Ubiquiti wireless devices) and generating easily identifiable output files.
