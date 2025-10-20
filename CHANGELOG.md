# Changelog

All significant changes to the project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-10-15

### Added
- Complete inventory system for Mikrotik RouterOS routers
- API client for connecting and collecting data from RouterOS (`mikrotik-client.py`)
- Pydantic data models for validation (`models.py`)
- Network topology analyzer (`analyzer.py`)
- Inventory manager with JSON/YAML export (`inventory.py`)
- Main orchestrator script (`main.py`)
- Utility functions for common operations (`utils.py`)

#### Data Collection
- Network interfaces (`/interface`)
- Wireless interfaces with SSID/mode details (`/interface/wireless`)
- IP Addresses (`/ip/address`)
- Neighbor discovery (`/ip/neighbor`)
- Active PPPoE connections (`/ppp/active`)
- PPPoE secrets (`/ppp/secret`)
- System resources (`/system/resource`)
- Router identity (`/system/identity`)

#### Analysis
- Identification of backbone links between routers
- Identification of Point-to-Point (PTP) links
- Identification of Point-to-Multipoint (PTMP) links
- Identification of PPPoE client-server connections
- Detection of configuration anomalies:
  - Multiple IPs on the same interface
  - Disabled interfaces with active IPs
  - Neighbors not present in inventory
  - Inactive PPPoE accounts
  - Interfaces without comments
  - Outdated RouterOS versions

#### Output
- Structured JSON export
- Human-readable YAML export
- Text summary with statistics
- Progress bar and colored output with Rich
- Detailed logging to file and console

#### Configuration
- YAML file for router configuration and credentials
- Support for default and per-router credentials
- Output and logging configuration
- Support for parallel data collection
- Retry configuration for failures
- Configuration template (`config.yaml.example`)

#### Documentation
- Complete README with instructions
- Quick Start Guide (`QUICKSTART.md`)
- API RouterOS reference (`docs/ROUTEROS_API.md`)
- Examples of advanced configurations (`docs/ADVANCED_CONFIG.md`)
- Connection test script (`examples/test-connection.py`)
- Unit tests for models (`tests/test_models.py`)

#### Development
- Setup pyproject.toml with dependencies
- Configuration .gitignore for sensitive files
- Pre-commit hooks configuration
- Docker support (Dockerfile and compose.yaml)
- Complete type hints
- PEP 257 compliant docstrings

### Dependencies
- `librouteros>=3.2.1` - RouterOS API client
- `pydantic>=2.0.0` - Data validation
- `pyyaml>=6.0` - YAML parsing
- `python-dotenv>=1.0.0` - Environment variables
- `rich>=13.0.0` - Terminal formatting

### Configuration
- Python 3.9+ required
- RouterOS API enabled on port 8728
- Read-only user recommended for security

## [Unreleased]

### Planned
- [ ] Support for API-SSL (port 8729)
- [ ] Export in Prometheus format
- [ ] Integration with Grafana for visualization
- [ ] Email notifications for critical anomalies
- [ ] Web dashboard for inventory visualization
- [ ] Diff between inventories for change tracking
- [ ] Support for configuration backups
- [ ] Export topology diagrams (Graphviz/Mermaid)
- [ ] REST API for inventory queries
- [ ] Support for databases (PostgreSQL/SQLite) for storage
- [ ] Inventory historization
- [ ] Advanced alerting
- [ ] Support for other vendors (Ubiquiti, Cisco)

### Future Enhancements
- [ ] Machine learning for anomaly detection
- [ ] Failure prediction based on trends
- [ ] Automatic configuration optimization
- [ ] Compliance checking (best practices)
- [ ] Integration with NetBox/phpIPAM
- [ ] SNMP support as fallback
- [ ] Interactive CLI
- [ ] Plugin system for custom extensions

---

## Version History

### Version Numbering

We use Semantic Versioning:
- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): Backward-compatible new features
- **PATCH** (0.0.X): Bug fixes

### Release Schedule

- **Patch releases**: As needed for critical bugs
- **Minor releases**: Monthly with new features
- **Major releases**: When there are significant breaking changes
