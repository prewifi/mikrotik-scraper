# Architecture Overview

This document describes the architecture of the Mikrotik Network Inventory system.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                   (Orchestration Layer)                          │
│  - Configuration loading                                         │
│  - Logging setup                                                 │
│  - Router data collection coordination                           │
│  - Analysis orchestration                                        │
│  - Output generation                                             │
└───────────────┬─────────────────────────────────────────────────┘
                │
       ┌────────┴────────┐
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│mikrotik-     │  │  analyzer.py │
│client.py     │  │              │
│              │  │  - Link      │
│ - RouterOS   │  │    detection │
│   API client │  │  - Anomaly   │
│ - Data       │  │    detection │
│   collection │  │  - Topology  │
│              │  │    analysis  │
└──────┬───────┘  └──────┬───────┘
       │                 │
       │                 │
       ▼                 ▼
┌─────────────────────────────────┐
│         models.py                │
│      (Data Models)               │
│  - Router                        │
│  - Interface                     │
│  - IPAddress                     │
│  - Neighbor                      │
│  - PPPoE                         │
│  - Link                          │
│  - Anomaly                       │
│  - NetworkInventory              │
└──────────────┬──────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│       inventory.py               │
│    (Persistence Layer)           │
│  - JSON export/import            │
│  - YAML export/import            │
│  - Summary generation            │
└──────────────────────────────────┘
```

## Main Components

### 1. main.py - Orchestrator
**Responsibilities**:
- Application entry point
- Configuration loading from YAML
- Logging setup and Rich console
- Data collection coordination (sequential or parallel)
- Analysis invocation
- Output generation

**Execution Flow**:
1. Parse CLI arguments
2. Load configuration
3. Setup logging
4. Iterate over routers and collect data
5. Pass data to the analyzer
6. Save results via inventory manager

### 2. mikrotik-client.py - API Client
**Responsibilities**:
- RouterOS API connection management
- API command execution
- API response parsing
- Data conversion into Pydantic models

**Key Methods**:
- `connect()`: Establish connection
- `get_system_identity()`: Router identity
- `get_system_resource()`: System resources
- `get_interfaces()`: Interface list
- `get_ip_addresses()`: IP addresses
- `get_neighbors()`: Neighbor discovery
- `get_pppoe_active()`: Active PPPoE
- `get_pppoe_secrets()`: PPPoE secrets
- `collect_all_data()`: Complete data collection

**Dependencies**:
- `librouteros`: RouterOS API library
- `models`: Data models

### 3. models.py - Data Models
**Responsibilities**:
- Data structure definitions
- Data validation with Pydantic
- Complete type hints
- JSON/YAML serialization

**Key Models**:
- `Router`: Complete router with all data
- `Interface`: Network interface
- `IPAddress`: IP address
- `Neighbor`: Nearby device
- `PPPoEActive`: Active PPPoE connection
- `PPPoESecret`: PPPoE credential
- `Link`: Link between devices
- `Anomaly`: Detected anomaly
- `NetworkInventory`: Complete inventory

**Enums**:
- `LinkType`: Link types (BACKBONE, PTP, PTMP, PPPOE)
- `InterfaceType`: Interface types

### 4. analyzer.py - Network Analyzer
**Responsibilities**:
- Network topology analysis
- Router link identification
- Anomaly detection
- Statistics calculation

**Implemented Analyses**:
- **Link Detection**:
  - Neighbor-based: Direct links via neighbor discovery
  - Interface-based: Link type determination (PTP/PTMP/backbone)
  - PPPoE: Client-server relationships

- **Anomaly Detection**:
  - Multiple IPs per interface
  - Disabled interfaces with IPs
  - Unknown neighbors
  - Inactive PPPoE secrets
  - Uncommented interfaces
  - Outdated RouterOS versions

**Key Methods**:
- `analyze_neighbor_links()`: Identify links from neighbors
- `analyze_pppoe_links()`: Identify PPPoE connections
- `detect_anomalies()`: Detect anomalies
- `analyze()`: Complete analysis

### 5. inventory.py - Persistence Layer
**Responsibilities**:
- Inventory saving to files
- Inventory loading from files
- Human-readable summary generation
- Output directory management

**Supported Formats**:
- **JSON**: Structured, machine-readable
- **YAML**: Human-readable, same content as JSON
- **Summary**: Text report with statistics

**Methods**:
- `save_json()`: JSON export
- `save_yaml()`: YAML export
- `save_summary()`: Generate text summary
- `load_json()`: JSON import
- `load_yaml()`: YAML import
- `list_inventories()`: List saved files
- `get_latest_inventory()`: Latest inventory

### 6. utils.py - Utility Functions
**Responsibilities**:
- Common helper functions
- IP validation
- CIDR parsing
- Data formatting

**Functions**:
- `is_valid_ip()`: Validate IP
- `parse_cidr()`: Parse CIDR notation
- `get_network_from_ip()`: Extract network from IP
- `format_uptime()`: Format uptime
- `sanitize_interface_name()`: Sanitize names
- `bytes_to_human()`: Convert bytes to human-readable format

## Data Flow

```
config.yaml
    │
    ▼
[main.py loads config]
    │
    ├─────────────────────────┐
    │                         │
    ▼                         ▼
[For each router]      [Parallel workers]
    │                         │
    ▼                         ▼
[MikrotikClient.connect()]
    │
    ▼
[Collect data via API]
    │
    ├─── /system/identity
    ├─── /system/resource
    ├─── /interface
    ├─── /ip/address
    ├─── /ip/neighbor
    ├─── /ppp/active
    └─── /ppp/secret
    │
    ▼
[Create Router model]
    │
    ▼
[List[Router]]
    │
    ▼
[NetworkAnalyzer.analyze()]
    │
    ├─── analyze_neighbor_links()
    ├─── analyze_pppoe_links()
    └─── detect_anomalies()
    │
    ▼
[NetworkInventory]
    │
    ▼
[InventoryManager.save_*()]
    │
    ├─── inventory_*.json
    ├─── inventory_*.yaml
    └─── summary_*.txt
```

## Configuration Flow

```yaml
config.yaml
├── default_credentials
│   ├── username
│   ├── password
│   ├── port
│   └── timeout
├── routers[]
│   ├── ip (required)
│   ├── username (optional, uses default)
│   ├── password (optional, uses default)
│   ├── port (optional, uses default)
│   └── timeout (optional, uses default)
├── output
│   ├── directory
│   └── formats[]
├── logging
│   ├── level
│   ├── file
│   └── console
└── collection
    ├── parallel
    ├── max_workers
    ├── retry_failed
    └── retry_attempts
```

## Error Handling

### Connection Errors
- Caught in `MikrotikClient.connect()`
- Logged and saved in `Router.connection_error`
- Router marked with `connection_successful=False`
- Execution continues with other routers

### API Errors
- Caught per command in `_execute_command()`
- Returns empty list in case of error
- Error details logged
- Collection continues with other commands

### Parse Errors
- Handled by Pydantic validation
- Field default values prevent crashes
- Optional fields for missing data

### File I/O Errors
- Handled in `InventoryManager`
- Detailed error logging
- Exceptions re-raised for caller handling

## Extension Points

### 1. New API Commands
Add in `mikrotik-client.py`:
```python
def get_new_data(self) -> List[NewModel]:
    result = self._execute_command("/new/path")
    return [NewModel(**item) for item in result]
```

### 2. New Analyses
Add in `analyzer.py`:
```python
def _check_new_anomaly(self, router: Router) -> List[Anomaly]:
    # Custom logic
    return anomalies
```

### 3. New Export Formats
Add in `inventory.py`:
```python
def save_custom_format(self, inventory: NetworkInventory) -> Path:
    # Custom serialization
    return filepath
```

### 4. Custom Models
Extend in `models.py`:
```python
class CustomData(BaseModel):
    # Custom fields
    pass

# Add to Router
class Router(BaseModel):
    custom_data: Optional[CustomData] = None
```

## Performance Considerations

### Parallel Collection
- Configurable via `collection.parallel`
- Max workers limitable to avoid overload
- Trade-off: speed vs network/CPU load

### Memory Usage
- One Router object ~ 10-50 KB
- 100 routers ~ 1-5 MB
- NetworkInventory in memory
- GC automatic after serialization

### API Latency
- Timeout configurable for routers
- Optional retry logic
- Parallel reduces total time

### File I/O
- Batch write for all formats
- Buffered I/O for summary
- Atomic writes (temp + rename)

## Security Considerations

### Credentials
- Never log passwords
- config.yaml in .gitignore
- Support for environment variables
- File permissions (chmod 600)

### API Access
- Read-only user recommended
- IP restriction on RouterOS
- Audit logging on router

### Output Files
- May contain sensitive info
- Protect output directory
- Consider encryption at rest

## Testing Strategy

### Unit Tests
- `tests/test_models.py`: Model validation
- Mock RouterOS API responses
- Test error handling

### Integration Tests
- Test with real router (development)
- Validate end-to-end flow
- Performance benchmarks

### Manual Testing
- `examples/test-connection.py`: Single router test
- Verify output files
- Review summary reports

## Dependencies Graph

```
main.py
├── mikrotik-client.py
│   ├── librouteros
│   └── models.py
│       └── pydantic
├── analyzer.py
│   └── models.py
├── inventory.py
│   ├── models.py
│   └── pyyaml
└── utils.py
    └── ipaddress (stdlib)
```

## Deployment Options

### 1. Standalone Script
```bash
python src/main.py -c config.yaml
```

### 2. Scheduled (Cron)
```cron
0 2 * * * /usr/bin/python3 /opt/mikrotik-inventory/src/main.py
```

### 3. Docker Container
```bash
docker-compose up
```

### 4. Systemd Service
```ini
[Service]
ExecStart=/usr/bin/python3 /opt/mikrotik-inventory/src/main.py
```

## Future Architecture

### Planned Enhancements
1. **Database Backend**: PostgreSQL for persistent storage
2. **REST API**: Flask/FastAPI for inventory querying
3. **Web Dashboard**: React frontend for visualization
4. **Message Queue**: Celery for job scheduling
5. **Caching**: Redis for performance
6. **Monitoring**: Prometheus metrics export

---

**Note**: This architecture is designed to be modular and extensible, allowing easy customizations and future integrations.
