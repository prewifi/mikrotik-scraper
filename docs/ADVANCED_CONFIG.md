# Advanced Configuration Examples

This guide provides advanced configurations for specific use cases.

## 1. Multi-Site Configuration

To manage routers in different locations/networks:

```yaml
# config-multisite.yaml

default_credentials:
  username: "admin"
  password: "default-pass"
  port: 8728
  timeout: 10

# Headquarters
routers:
  # Central backbone
  - ip: "10.0.0.1"
    username: "admin-site-a"
    password: "pass-site-a"
  - ip: "10.0.0.2"
    username: "admin-site-a"
    password: "pass-site-a"

  # Site B
  - ip: "10.1.0.1"
    username: "admin-site-b"
    password: "pass-site-b"
  - ip: "10.1.0.2"
    username: "admin-site-b"
    password: "pass-site-b"

  # Site C (with higher timeout for slow connection)
  - ip: "10.2.0.1"
    username: "admin-site-c"
    password: "pass-site-c"
    timeout: 20

output:
  directory: "output/multisite"
  formats:
    - "json"
    - "yaml"
    - "summary"

collection:
  parallel: true
  max_workers: 10
  retry_failed: true
  retry_attempts: 3
```

## 2. Configuration with Groups

Organize routers by function/type:

```yaml
# config-groups.yaml

default_credentials:
  username: "monitoring"
  password: "readonly-pass"

# Backbone routers (core network)
backbone_routers:
  - ip: "10.0.0.1"
  - ip: "10.0.0.2"
  - ip: "10.0.0.3"

# Access Points / PTMP
access_points:
  - ip: "10.10.1.1"
  - ip: "10.10.1.2"
  - ip: "10.10.2.1"

# PPPoE Servers
pppoe_servers:
  - ip: "10.20.0.1"
  - ip: "10.20.0.2"

# Gateway / Border routers
gateways:
  - ip: "10.0.0.254"
    username: "admin-gw"
    password: "secure-gw-pass"

# Merge all for processing
routers: >
  {{ backbone_routers + access_points + pppoe_servers + gateways }}

logging:
  level: "INFO"
  file: "inventory-grouped.log"
  console: true
```

## 3. High-Performance Configuration

For very large networks (100+ routers):

```yaml
# config-highperf.yaml

default_credentials:
  username: "api-reader"
  password: "secure-pass"
  timeout: 5  # Shorter timeout

routers:
  # ... long list of routers ...

output:
  directory: "output/highperf"
  formats:
    - "json"  # JSON only for speed

collection:
  parallel: true
  max_workers: 20  # Many parallel workers
  retry_failed: false  # Do not retry for speed
  retry_attempts: 0

logging:
  level: "WARNING"  # Only warnings/errors for speed
  file: "highperf.log"
  console: false  # Disable console output for speed
```

## 4. Debug/Development Configuration

For troubleshooting and development:

```yaml
# config-debug.yaml

default_credentials:
  username: "admin"
  password: "test-pass"

routers:
  # Only a few routers for testing
  - ip: "192.168.88.1"  # Local test router

output:
  directory: "output/debug"
  formats:
    - "json"
    - "yaml"
    - "summary"

collection:
  parallel: false  # Sequential for debugging
  max_workers: 1
  retry_failed: true
  retry_attempts: 3

logging:
  level: "DEBUG"  # All details
  file: "debug.log"
  console: true
```

## 5. Secure Configuration with Vault

Using environment variables for passwords:

```yaml
# config-secure.yaml

default_credentials:
  username: "${MIKROTIK_USERNAME}"
  password: "${MIKROTIK_PASSWORD}"
  port: 8728

routers:
  - ip: "10.0.0.1"
  - ip: "10.0.0.2"
    username: "${MIKROTIK_ADMIN_USERNAME}"
    password: "${MIKROTIK_ADMIN_PASSWORD}"

output:
  directory: "${OUTPUT_DIR:-output}"
  formats:
    - "json"
    - "summary"
```

Then run with:

```bash
export MIKROTIK_USERNAME="admin"
export MIKROTIK_PASSWORD="your-secure-password"
export OUTPUT_DIR="/secure/path/output"

python src/main.py -c config-secure.yaml
```

## 6. Scheduled Configuration (Cron)

For scheduled executions:

```yaml
# config-scheduled.yaml

default_credentials:
  username: "scheduler"
  password: "auto-pass"

routers:
  - ip: "10.0.0.1"
  - ip: "10.0.0.2"
  # ... other routers

output:
  directory: "/var/log/mikrotik-inventory/$(date +%Y%m)"
  formats:
    - "json"
    - "summary"

collection:
  parallel: true
  max_workers: 10
  retry_failed: true
  retry_attempts: 2

logging:
  level: "INFO"
  file: "/var/log/mikrotik-inventory/scheduler.log"
  console: false
```

Crontab entry:

```bash
# Every day at 02:00
0 2 * * * cd /opt/mikrotik-inventory && /usr/bin/python3 src/main.py -c config-scheduled.yaml >> /var/log/mikrotik-inventory/cron.log 2>&1

# Every Monday at 01:00
0 1 * * 1 cd /opt/mikrotik-inventory && /usr/bin/python3 src/main.py -c config-scheduled.yaml --json-only
```

## 7. Monitoring Configuration

Integration with monitoring systems:

```yaml
# config-monitoring.yaml

default_credentials:
  username: "monitoring"
  password: "mon-pass"

routers:
  - ip: "10.0.0.1"
  - ip: "10.0.0.2"

output:
  directory: "/var/lib/monitoring/mikrotik"
  formats:
    - "json"  # For automatic parsing

collection:
  parallel: true
  max_workers: 15
  retry_failed: true
  retry_attempts: 2

logging:
  level: "WARNING"
  file: "/var/log/monitoring/mikrotik-collector.log"
  console: false

# Custom configurations for monitoring
monitoring:
  export_prometheus: true
  prometheus_port: 9100
  alert_on_anomalies: true
  alert_critical_only: false
```

## 8. Network Segments Configuration

For segmented networks for security:

```yaml
# config-segments.yaml

default_credentials:
  username: "netadmin"
  password: "base-pass"

# Segment 1: Management Network
routers:
  - ip: "172.16.1.1"
  - ip: "172.16.1.2"

  # Segment 2: Customer Network
  - ip: "172.16.10.1"
    username: "customer-admin"
    password: "customer-pass"
  - ip: "172.16.10.2"
    username: "customer-admin"
    password: "customer-pass"

  # Segment 3: Guest Network
  - ip: "172.16.20.1"
    username: "guest-admin"
    password: "guest-pass"

output:
  directory: "output/segments"
  formats:
    - "json"
    - "yaml"

collection:
  parallel: true
  max_workers: 5
```

## 9. Test Subset Configuration

To test changes on a subset of routers:

```yaml
# config-test.yaml

default_credentials:
  username: "admin"
  password: "test-pass"

# Test only on 2-3 representative routers
routers:
  - ip: "10.0.0.1"  # Backbone router
  - ip: "10.10.1.1"  # Access point
  - ip: "10.20.0.1"  # PPPoE server

output:
  directory: "output/test"
  formats:
    - "json"
    - "yaml"
    - "summary"

collection:
  parallel: false
  retry_failed: true

logging:
  level: "DEBUG"
  console: true
```

## 10. Production Configuration

Optimal configuration for production:

```yaml
# config-production.yaml

default_credentials:
  username: "inventory-prod"
  password: "prod-secure-password-here"
  port: 8728
  timeout: 15

routers:
  # Include external file with router list
  # !include routers-list.yaml

output:
  directory: "/data/mikrotik-inventory/production"
  formats:
    - "json"
    - "summary"

collection:
  parallel: true
  max_workers: 15
  retry_failed: true
  retry_attempts: 2

logging:
  level: "INFO"
  file: "/var/log/mikrotik-inventory/production.log"
  console: false

# Notifications
notifications:
  enabled: true
  email:
    smtp_server: "smtp.company.com"
    from: "mikrotik-inventory@company.com"
    to: ["netadmin@company.com"]
    on_error: true
    on_complete: false
```

## Using the Examples

To use a specific configuration:

```bash
python src/main.py -c config-multisite.yaml
python src/main.py -c config-debug.yaml
python src/main.py -c config-production.yaml
```

## Tips

1. **Always test with config-debug before production**
2. **Use parallel: true only if you have enough bandwidth**
3. **Increase timeout for slow/saturated connections**
4. **Use read-only credentials when possible**
5. **Monitor logs to optimize max_workers**
