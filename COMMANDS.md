# MikroTik Scraper

Inventory and automation system for MikroTik RouterBoards.

## Available Commands

### Inventory Collection (Default)
```bash
python3 src/main.py
python3 src/main.py -c config.yaml  # Specify configuration file
python3 src/main.py -o output_dir    # Override output directory
python3 src/main.py --json-only      # Save only in JSON format
python3 src/main.py --yaml-only      # Save only in YAML format
```

### Backup
```bash
python3 src/main.py --backup          # Inventory + Backup
python3 src/main.py --backup-only     # Backup only (.backup and .rsc files)
```

### IP Services Configuration
```bash
python3 src/main.py --configure-services       # Inventory + Configure IP services
python3 src/main.py --configure-services-only  # Configure IP services only
```

### User and Group Configuration
```bash
python3 src/main.py --configure-users       # Inventory + Configure users
python3 src/main.py --configure-users-only  # Configure users/groups only
```

### Syslog Configuration
```bash
python3 src/main.py --configure-syslog       # Inventory + Configure syslog
python3 src/main.py --configure-syslog-only  # Configure syslog only
```

## Running with Docker

```bash
# Development
docker compose -f compose.dev.yaml up -d
docker exec mikrotik-scraper-dev python3 src/main.py --backup-only

# Production
docker compose -f compose.prod.yaml up -d
docker exec mikrotik-scraper-prod python3 src/main.py
```

## Execution Report

A report is generated in `results/` after each operation:
- `backup_report_YYYYMMDD_HHMMSS.txt`

The report contains:
- Total/Success/Failed summary
- List of successful routers
- List of failed routers with error details

## Configuration

Copy `config.yaml.example` to `config.yaml` and customize:
- `routers`: List of RouterBoards to manage
- `backup`: Backup settings
- `ip_services`: IP services configuration
- `user_management`: Users and groups
- `syslog`: Remote logging configuration
