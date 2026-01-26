# Mikrotik Network Inventory System

Complete Python system for automated network inventory collection, analysis, and management for Mikrotik RouterOS routers.

## Features

- **RouterOS API Connection**: Uses `routeros-api` to connect to Mikrotik routers via API (compatible with RouterOS 6.x and 7.x)
- **Comprehensive Data Collection**: Collects information on:
  - Network interfaces (`/interface`)
  - IP Neighbors (`/ip/neighbor`)
  - IP Addresses (`/ip/address`)
  - Active PPPoE connections and secrets (`/ppp/active`, `/ppp/secret`)
  - System resources (`/system/resource`, `/system/identity`)

- **Multi-format Export**: Saves inventory in:
  - JSON (for automated processing)
  - YAML (human-readable)
  - Text summary (readable report)

- **Advanced Logging**: Uses Rich for colored output and progress bars

## Tested and Functional

The system has been successfully tested on:
- RouterOS 6.42.1 (stable) on MikroTik RB2011iL
- Complete collection of 24 interfaces, 11 neighbors, 6 PPPoE connections
- Verified JSON/YAML export

## Requirements

- Python 3.9+
- RouterOS API enabled on Mikrotik routers (port 8728)
- Router access credentials

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/prewifi/mikrotik-scraper.git
cd mikrotik-scraper
```

### 2. Install dependencies

```bash
pip install -e .
```

or for the development environment:

```bash
pip install -e ".[dev]"
```

### 3. Configure the routers

Copy the example configuration file and modify it with your routers:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` and add your routers:

```yaml
default_credentials:
  username: "admin"
  password: "your-password"
  port: 8728
  timeout: 10

routers:
  - ip: "192.168.1.1"
  - ip: "192.168.1.2"
    username: "custom-user"
    password: "custom-password"
  # Add more routers...
```

**IMPORTANT**: Do not commit `config.yaml` to the repository! It contains sensitive credentials.

## Usage

### Basic execution

```bash
python src/main.py
```

### Available options

```bash
python src/main.py --help
```

Options:
- `-c, --config FILE`: Specify an alternative configuration file (default: `config.yaml`)
- `-o, --output-dir DIR`: Output directory for generated files
- `--json-only`: Save only in JSON format
- `--yaml-only`: Save only in YAML format

### Examples

```bash
# Use an alternative configuration
python src/main.py -c config-production.yaml

# Save only in JSON format
python src/main.py --json-only

# Specify a custom output directory
python src/main.py -o /path/to/output
```

## Project Structure

```
mikrotik-scraper/
├── src/
│   ├── __init__.py
│   ├── main.py              # Main entry point
│   ├── models.py            # Pydantic data models
│   ├── mikrotik-client.py   # RouterOS API client
│   ├── analyzer.py          # Network topology analyzer
│   └── inventory.py         # Inventory save/load management
├── config.yaml.example      # Configuration template
├── pyproject.toml          # Project and dependency configuration
├── requirements-dev.txt    # Development dependencies
└── README.md               # This documentation
```

## Output

The system generates three types of files in the `output/` directory:

### 1. JSON (`inventory_YYYYMMDD_HHMMSS.json`)
Structured format for automated processing:
```json
{
  "routers": [...],
  "links": [...],
  "anomalies": [...],
  "stats": {...}
}
```

### 2. YAML (`inventory_YYYYMMDD_HHMMSS.yaml`)
Human-readable format identical to JSON but more readable.

### 3. Summary (`summary_YYYYMMDD_HHMMSS.txt`)
Text report with:
- General statistics
- List of routers with status
- Identified links by type
- Detected anomalies with suggestions

## Implemented Analysis

### Link Identification

1. **Backbone Links**: Ethernet connections between known routers
2. **PTP (Point-to-Point)**: Wireless links in station mode
3. **PTMP (Point-to-Multipoint)**: Wireless links in ap-bridge mode
4. **PPPoE**: Active PPPoE client-server connections

### Anomaly Detection

- Interfaces with multiple IP addresses
- Disabled interfaces with active IPs
- Neighbors not present in the inventory
- Many inactive PPPoE accounts
- Interfaces without descriptive comments
- Obsolete RouterOS versions

## Advanced Configuration

### Parallel Collection

To speed up collection on many routers:

```yaml
collection:
  parallel: true
  max_workers: 10
  retry_failed: true
  retry_attempts: 2
```

### Logging

Configure the logging level:

```yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "mikrotik-inventory.log"
  console: true
```

## Troubleshooting

### Router connection error

1. Check that the API is enabled on the router:
   ```
   /ip service print
   ```
   The API must be enabled on port 8728

2. Check the firewall:
   ```
   /ip firewall filter print
   ```
   Make sure that port 8728 is accessible

3. Verify the credentials in `config.yaml`

### Issues with librouteros

If you have problems with the library, try:

```bash
pip uninstall librouteros
pip install librouteros==3.2.1
```

## Logs

Logs are saved in `mikrotik-inventory.log` and include:
- Timestamps of operations
- Success/failure of connections
- Data collected for each router
- Errors and warnings

## Security

- **NEVER** commit `config.yaml` with real credentials
- Use appropriate file permissions: `chmod 600 config.yaml`
- Consider using environment variables for sensitive passwords
- Limit API access to only necessary IPs on the routers

## Contributing

To contribute to the project:

1. Fork the repository
2. Create a branch for the feature (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request


## Acknowledgments

- [librouteros](https://github.com/luqasz/librouteros) - RouterOS API client
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---
