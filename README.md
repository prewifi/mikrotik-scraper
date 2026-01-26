# Mikrotik Network Inventory System

Complete system for automated network inventory collection, analysis, backup, and management for Mikrotik RouterOS routers.

## Features

- **RouterOS API Connection**: Uses `routeros-api` to connect to Mikrotik routers via API (compatible with RouterOS 6.x and 7.x)
- **Comprehensive Data Collection**: Collects information on:
  - Network interfaces (`/interface`)
  - IP Neighbors (`/ip/neighbor`)
  - IP Addresses (`/ip/address`)
  - Active PPPoE connections and secrets (`/ppp/active`, `/ppp/secret`)
  - System resources (`/system/resource`, `/system/identity`)
- **Automated Backups**: Creates and downloads backups (`.backup` and `.rsc`)
- **Configuration Management**: 
  - Manage IP Services (api, ssh, www, etc.)
  - Manage Users and Groups
  - Configure Remote Syslog
- **Multi-format Export**: Saves inventory in JSON, YAML, and Text summary
- **Advanced Logging**: Uses Rich for colored output and progress bars

## Requirements

- Docker and Docker Compose
- RouterOS API enabled on Mikrotik routers (port 8728)
- Router access credentials

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/prewifi/mikrotik-scraper.git
cd mikrotik-scraper
```

### 2. Configure the routers

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

### 3. Start the Container

Run the system using Docker Compose:

```bash
# Production
docker compose -f compose.prod.yaml up -d
```

## Usage

Once the container is running, you can execute commands using `docker exec`.

### Inventory Collection (Default)

```bash
docker exec mikrotik-scraper-prod python3 src/main.py
```

### Backup Operations

Create and download backups (`.backup` and `.rsc`):

```bash
# Inventory + Backup
docker exec mikrotik-scraper-prod python3 src/main.py --backup

# Backup Only (skip inventory)
docker exec mikrotik-scraper-prod python3 src/main.py --backup-only
```

### Configuration Management

**IP Services:**
```bash
docker exec mikrotik-scraper-prod python3 src/main.py --configure-services
```

**Users and Groups:**
```bash
docker exec mikrotik-scraper-prod python3 src/main.py --configure-users
```

**Syslog:**
```bash
docker exec mikrotik-scraper-prod python3 src/main.py --configure-syslog
```

### Available Options

```bash
docker exec mikrotik-scraper-prod python3 src/main.py --help
```

Common options:
- `-c, --config FILE`: Specify an alternative configuration file (default: `config.yaml`)
- `-o, --output-dir DIR`: Output directory for generated files
- `--json-only`: Save only in JSON format
- `--yaml-only`: Save only in YAML format

## Output

The system generates files in the `results/` directory (mapped volume):

### 1. Execution Reports
After each operation, a report is generated:
- `backup_report_YYYYMMDD_HHMMSS.txt`

### 2. Inventory Files
- JSON: `inventory_YYYYMMDD_HHMMSS.json`
- YAML: `inventory_YYYYMMDD_HHMMSS.yaml`
- Summary: `summary_YYYYMMDD_HHMMSS.txt`

## Local Development (Python)

If you prefer to run the script locally without Docker:

1. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Run the script:
   ```bash
   python src/main.py
   ```

## Project Structure

```
mikrotik-scraper/
├── src/
│   ├── main.py              # Main entry point
│   ├── models.py            # Pydantic data models
│   ├── mikrotik-client.py   # RouterOS API client
│   ├── backup_manager.py    # Backup logic
│   ├── sftp_client.py       # SFTP/SSH client
│   └── ...
├── config.yaml.example      # Configuration template
├── compose.prod.yaml        # Production Docker Compose
├── compose.dev.yaml         # Development Docker Compose
├── requirements.txt         # Dependencies
└── README.md               # This documentation
```

## Security

- **NEVER** commit `config.yaml` with real credentials
- Use appropriate file permissions: `chmod 600 config.yaml`
- Limit API access to only necessary IPs on the routers

## Acknowledgments

- [librouteros](https://github.com/luqasz/librouteros) - RouterOS API client
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
