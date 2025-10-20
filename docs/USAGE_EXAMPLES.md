# Usage Examples

Practical usage examples for the Mikrotik Network Inventory system.

## 1. First Use - Basic Setup

```bash
# 1. Install dependencies
pip install -e .

# 2. Copy example configuration
cp config.yaml.example config.yaml

# 3. Edit config.yaml
nano config.yaml

# 4. Test single router connection
python examples/test-connection.py 192.168.1.1 admin password

# 5. Run complete inventory
python src/main.py
```

## 2. Scenario: Small Network (5-10 Routers)

**Configuration**: config.yaml
```yaml
default_credentials:
  username: "admin"
  password: "mypassword"

routers:
  - ip: "192.168.1.1"  # Main router
  - ip: "192.168.1.2"  # AP Zone A
  - ip: "192.168.1.3"  # AP Zone B
  - ip: "192.168.1.4"  # PPPoE Server
  - ip: "192.168.1.5"  # Gateway

output:
  directory: "output"
  formats: ["json", "yaml", "summary"]

collection:
  parallel: false  # Sequential for small networks
```

**Execution**:
```bash
python src/main.py
```

**Output**:
- `output/inventory_20241015_143022.json`
- `output/inventory_20241015_143022.yaml`
- `output/summary_20241015_143022.txt`

## 3. Scenario: Medium Network (50+ Routers)

**Configuration**: config-production.yaml
```yaml
default_credentials:
  username: "monitoring"
  password: "secure-pass"
  timeout: 15

routers:
  # Backbone
  - ip: "10.0.0.1"
  - ip: "10.0.0.2"
  - ip: "10.0.0.3"
  
  # Access Points
  - ip: "10.10.1.1"
  - ip: "10.10.1.2"
  # ... other 45+ routers
  
output:
  directory: "output/production"
  formats: ["json", "summary"]

collection:
  parallel: true
  max_workers: 10
  retry_failed: true
  retry_attempts: 2

logging:
  level: "INFO"
  file: "production.log"
```

**Execution**:
```bash
python src/main.py -c config-production.yaml
```

## 4. Scenario: Automatic Daily Monitoring

**Cron Setup**:
```bash
# Edit crontab
crontab -e

# Add (execution at 2 AM daily)
0 2 * * * cd /opt/mikrotik-inventory && /usr/bin/python3 src/main.py -c config-production.yaml >> /var/log/mikrotik-cron.log 2>&1
```

**Script Wrapper** (optional): `scripts/daily-inventory.sh`
```bash
#!/bin/bash

SCRIPT_DIR="/opt/mikrotik-inventory"
LOG_DIR="/var/log/mikrotik-inventory"
DATE=$(date +%Y%m%d)

cd $SCRIPT_DIR

# Run inventory
python3 src/main.py -c config-production.yaml > "$LOG_DIR/run_$DATE.log" 2>&1

# Verify success
if [ $? -eq 0 ]; then
    echo "Inventory completed successfully" >> "$LOG_DIR/run_$DATE.log"
    
    # Optional: send email with summary
    mail -s "Mikrotik Inventory - $DATE" admin@example.com < output/summary_*.txt
else
    echo "Inventory FAILED" >> "$LOG_DIR/run_$DATE.log"
    # Notify error
    mail -s "Mikrotik Inventory ERROR - $DATE" admin@example.com < "$LOG_DIR/run_$DATE.log"
fi

# Cleanup old files (keep last 30 days)
find output/ -name "*.json" -mtime +30 -delete
find output/ -name "*.yaml" -mtime +30 -delete
find output/ -name "*.txt" -mtime +30 -delete
```

## 5. Scenario: Debug/Troubleshooting

**Test single router with maximum detail**:
```bash
# 1. Create debug config
cat > config-debug.yaml << EOF
default_credentials:
  username: "admin"
  password: "test"

routers:
  - ip: "192.168.88.1"

logging:
  level: "DEBUG"
  console: true

collection:
  parallel: false
EOF

# 2. Run with verbose output
python src/main.py -c config-debug.yaml 2>&1 | tee debug-output.log

# 3. Analyze log
grep ERROR debug-output.log
grep WARNING debug-output.log
```

## 6. Scenario: Compare Inventories

**Compare two inventories to see changes**:

```python
# scripts/compare-inventories.py
import json
import sys
from pathlib import Path

def load_inventory(path):
    with open(path) as f:
        return json.load(f)

def compare_routers(old, new):
    old_ips = {r['ip_address'] for r in old['routers']}
    new_ips = {r['ip_address'] for r in new['routers']}
    
    added = new_ips - old_ips
    removed = old_ips - new_ips
    
    print(f"Routers Added: {len(added)}")
    for ip in added:
        print(f"  + {ip}")
    
    print(f"\nRouters Removed: {len(removed)}")
    for ip in removed:
        print(f"  - {ip}")
    
    # Compare common routers
    common = old_ips & new_ips
    print(f"\nCommon Routers: {len(common)}")
    
    for ip in common:
        old_router = next(r for r in old['routers'] if r['ip_address'] == ip)
        new_router = next(r for r in new['routers'] if r['ip_address'] == ip)
        
        old_ifaces = len(old_router['interfaces'])
        new_ifaces = len(new_router['interfaces'])
        
        if old_ifaces != new_ifaces:
            print(f"  {ip}: Interfaces {old_ifaces} -> {new_ifaces}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare-inventories.py <old.json> <new.json>")
        sys.exit(1)
    
    old = load_inventory(sys.argv[1])
    new = load_inventory(sys.argv[2])
    
    compare_routers(old, new)
```

**Usage**:
```bash
python scripts/compare-inventories.py \
    output/inventory_20241001_020000.json \
    output/inventory_20241015_020000.json
```

## 7. Scenario: Export for Grafana/Prometheus

**Extract metrics for monitoring**:

```python
# scripts/export-metrics.py
import json
import sys
from datetime import datetime

def export_prometheus(inventory_path):
    with open(inventory_path) as f:
        inv = json.load(f)
    
    timestamp = int(datetime.now().timestamp() * 1000)
    
    # Example metrics
    print(f"# HELP mikrotik_routers_total Total number of routers")
    print(f"# TYPE mikrotik_routers_total gauge")
    print(f"mikrotik_routers_total {inv['stats']['total_routers']} {timestamp}")
    
    print(f"# HELP mikrotik_links_total Total number of links")
    print(f"# TYPE mikrotik_links_total gauge")
    print(f"mikrotik_links_total {inv['stats']['total_links']} {timestamp}")
    
    print(f"# HELP mikrotik_anomalies_total Total anomalies")
    print(f"# TYPE mikrotik_anomalies_total gauge")
    print(f"mikrotik_anomalies_total {inv['stats']['total_anomalies']} {timestamp}")
    
    # Per router metrics
    for router in inv['routers']:
        labels = f'identity="{router["identity"]}",ip="{router["ip_address"]}"'
        
        print(f"mikrotik_router_interfaces{{{labels}}} {len(router['interfaces'])}")
        print(f"mikrotik_router_neighbors{{{labels}}} {len(router['neighbors'])}")
        print(f"mikrotik_router_pppoe_active{{{labels}}} {len(router['pppoe_active'])}")

if __name__ == "__main__":
    export_prometheus(sys.argv[1])
```

**Usage**:
```bash
python scripts/export-metrics.py output/inventory_latest.json > metrics.prom
```

## 8. Scenario: Multi-Site with Different Credentials

**Configuration**: config-multisite.yaml
```yaml
default_credentials:
  username: "readonly"
  password: "default-pass"

routers:
  # Site A - Main office
  - ip: "10.0.0.1"
    username: "admin-sitea"
    password: "sitea-pass"
  - ip: "10.0.0.2"
    username: "admin-sitea"
    password: "sitea-pass"
  
  # Site B - Branch
  - ip: "10.1.0.1"
    username: "admin-siteb"
    password: "siteb-pass"
  
  # Site C - Use default credentials
  - ip: "10.2.0.1"

output:
  directory: "output/multisite"
  formats: ["json", "summary"]
```

**Execution**:
```bash
python src/main.py -c config-multisite.yaml
```

## 9. Scenario: Anomaly Analysis

**Extract only critical anomalies**:

```bash
# After execution, extract anomalies from JSON
jq '.anomalies[] | select(.severity=="critical")' output/inventory_*.json

# Or filter from summary
grep -A 3 "CRITICAL" output/summary_*.txt
```

**Python script for anomaly report**:
```python
# scripts/anomaly-report.py
import json
import sys
from collections import defaultdict

with open(sys.argv[1]) as f:
    inv = json.load(f)

# Group by type
by_type = defaultdict(list)
for anomaly in inv['anomalies']:
    by_type[anomaly['anomaly_type']].append(anomaly)

print("ANOMALY REPORT")
print("=" * 60)

for atype, anomalies in sorted(by_type.items()):
    print(f"\n{atype.upper()} ({len(anomalies)} occurrenze):")
    for a in anomalies[:5]:  # First 5
        print(f"  [{a['severity']}] {a['router']}: {a['description']}")
    if len(anomalies) > 5:
        print(f"  ... and {len(anomalies)-5}")
```

## 10. Scenario: Integration with Existing Scripts

**Use the inventory in other scripts**:

```python
#!/usr/bin/env python3
# scripts/my-custom-script.py

import json
from pathlib import Path

# Load latest inventory
inventory_dir = Path("output")
latest = sorted(inventory_dir.glob("inventory_*.json"))[-1]

with open(latest) as f:
    inventory = json.load(f)

# Process data
for router in inventory['routers']:
    if router['connection_successful']:
        print(f"Processing {router['identity']}...")
        
        # Do something with the data
        for interface in router['interfaces']:
            if interface['running']:
                print(f"  Active interface: {interface['name']}")
```

## Tips & Tricks

### 1. Quick Connectivity Check
```bash
# Quick test without saving
python src/main.py -c config.yaml --json-only -o /tmp
ls -lh /tmp/inventory_*.json
```

### 2. Output to Screen Only
```bash
# Temporarily modify config to not save files
python src/main.py | tee console-output.txt
```

### 3. Filter Specific Routers
```bash
# Create temporary config with subset
yq eval '.routers = .routers[0:5]' config.yaml > config-subset.yaml
python src/main.py -c config-subset.yaml
```

### 4. Export CSV for Excel
```python
# scripts/to-csv.py
import json, csv

with open('output/inventory.json') as f:
    inv = json.load(f)

with open('routers.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Identity', 'IP', 'Version', 'Interfaces', 'Neighbors'])
    
    for r in inv['routers']:
        version = r['system_resource']['version'] if r['system_resource'] else 'N/A'
        writer.writerow([
            r['identity'],
            r['ip_address'],
            version,
            len(r['interfaces']),
            len(r['neighbors'])
        ])
```

### 5. Alert on Critical Anomalies
```bash
# In wrapper script
CRITICAL_COUNT=$(jq '[.anomalies[] | select(.severity=="critical")] | length' output/inventory_*.json)

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "ALERT: $CRITICAL_COUNT critical anomalies detected!" | \
        mail -s "Mikrotik Inventory Alert" admin@example.com
fi
```

---

For other examples and use cases, see the complete documentation in README.md
