# RouterOS API Reference

This document describes the RouterOS API commands used by the system and the information collected.

## API Enablement

### Via CLI/SSH

```bash
/ip service enable api
/ip service set api port=8728
/ip service set api address=192.168.0.0/16  # Limit access to specific network
```

### Via WinBox

1. Go to `IP` → `Services`
2. Find `api` in the list
3. Double-click on `api`
4. Enable the service
5. Set `Available From` to limit access

## Used API Commands

### 1. System Identity

**Path**: `/system/identity`

**Purpose**: Gets the name/identity of the router

**Fields Used**:
- `name`: Router name/hostname

**Example Output**:
```json
{
  "name": "RouterBackbone-01"
}
```

---

### 2. System Resource

**Path**: `/system/resource`

**Purpose**: System information, version, hardware, resources

**Fields Used**:
- `uptime`: Router uptime
- `version`: RouterOS version
- `cpu`: CPU type
- `cpu-load`: CPU load (%)
- `free-memory`: Free memory (bytes)
- `total-memory`: Total memory (bytes)
- `architecture-name`: Architecture (e.g., MIPS, ARM)
- `board-name`: Device model

**Example Output**:
```json
{
  "uptime": "1w2d3h4m5s",
  "version": "6.49.6 (stable)",
  "cpu": "MIPS 24Kc V7.4",
  "cpu-load": 12,
  "free-memory": 50000000,
  "total-memory": 128000000,
  "architecture-name": "mipsbe",
  "board-name": "RB750Gr3"
}
```

---

### 3. Interfaces

**Path**: `/interface`

**Purpose**: List all network interfaces

**Fields Used**:
- `name`: Interface name (e.g., "ether1", "wlan1")
- `type`: Interface type (ether, bridge, wlan, vlan, etc.)
- `mtu`: Maximum Transmission Unit
- `mac-address`: MAC address
- `disabled`: If disabled (true/false)
- `running`: If active (true/false)
- `comment`: Descriptive comment

**Additional Path**: `/interface/wireless`

**Wireless Fields**:
- `ssid`: Wireless network name
- `mode`: Mode (ap-bridge, station, bridge, etc.)
- `frequency`: Operating frequency

**Example Output**:
```json
[
  {
    "name": "ether1",
    "type": "ether",
    "mtu": 1500,
    "mac-address": "AA:BB:CC:DD:EE:FF",
    "disabled": false,
    "running": true,
    "comment": "WAN"
  },
  {
    "name": "wlan1",
    "type": "wlan",
    "ssid": "BackbonePTP-01",
    "mode": "station",
    "frequency": "5180"
  }
]
```

---

### 4. IP Addresses

**Path**: `/ip/address`

**Purpose**: All configured IP addresses

**Fields Used**:
- `address`: IP address with CIDR (e.g., "192.168.1.1/24")
- `network`: Network address
- `interface`: Interface assigned to
- `disabled`: If disabled
- `comment`: Comment

**Example Output**:
```json
[
  {
    "address": "192.168.1.1/24",
    "network": "192.168.1.0",
    "interface": "bridge1",
    "disabled": false,
    "comment": "LAN"
  },
  {
    "address": "10.0.0.1/30",
    "network": "10.0.0.0",
    "interface": "ether1",
    "disabled": false,
    "comment": "P2P Link"
  }
]
```

---

### 5. IP Neighbors

**Path**: `/ip/neighbor`

**Purpose**: Neighboring devices discovered via LLDP/CDP/MNDP

**Fields Used**:
- `interface`: Local interface where it was seen
- `identity`: Name/identity of neighbor
- `address`: Neighbor IP address
- `platform`: Device platform
- `version`: Software version
- `mac-address`: Neighbor MAC address

**Example Output**:
```json
[
  {
    "interface": "ether2",
    "identity": "RouterBackbone-02",
    "address": "192.168.1.2",
    "platform": "MikroTik",
    "version": "6.49.6",
    "mac-address": "11:22:33:44:55:66"
  }
]
```

---

### 6. PPP Active

**Path**: `/ppp/active`

**Purpose**: Currently active PPPoE connections

**Fields Used**:
- `name`: Username/connection name
- `service`: Service name
- `caller-id`: Client MAC address
- `address`: IP assigned to client
- `uptime`: Connection uptime
- `encoding`: Encoding information

**Example Output**:
```json
[
  {
    "name": "client001",
    "service": "pppoe-service1",
    "caller-id": "AA:BB:CC:DD:EE:01",
    "address": "10.10.1.100",
    "uptime": "1d2h30m",
    "encoding": "MPPE128"
  }
]
```

---

### 7. PPP Secret

**Path**: `/ppp/secret`

**Purpose**: Configured PPPoE credentials (username/password)

**Fields Used**:
- `name`: Username
- `password`: Password (if readable)
- `service`: Associated service name
- `profile`: Applied profile
- `local-address`: Server IP (gateway)
- `remote-address`: Client IP or pool
- `disabled`: If disabled
- `comment`: Comment

**Example Output**:
```json
[
  {
    "name": "client001",
    "password": "secretpass",
    "service": "pppoe-service1",
    "profile": "default-profile",
    "local-address": "10.10.1.1",
    "remote-address": "10.10.1.100",
    "disabled": false,
    "comment": "Residential client zone A"
  }
]
```

---

## Required User Permissions

To collect all data, the API user must have at least the following permissions:

```bash
/user group add name=api-readonly \
  policy=read,api,!local,!telnet,!ssh,!ftp,!reboot,!write,!policy,!test,!winbox,!password,!web,!sniff,!sensitive,!romon,!rest-api
```

Or use the existing `read` group:

```bash
/user add name=api-reader group=read password=your-secure-password
```

## Security Best Practices

1. **Limit access IPs**:
   ```bash
   /ip service set api address=192.168.0.0/16
   ```

2. **Use strong passwords**:
   ```bash
   /user set admin password="ComplexP@ssw0rd123!"
   ```

3. **Create dedicated read-only user**:
   ```bash
   /user add name=inventory-reader group=read password="SecureReadOnlyPass"
   ```

4. **Monitor access**:
   ```bash
   /log print where topics~"api"
   ```

5. **Consider using certificates**:
   RouterOS supports API-SSL on port 8729 for encrypted connections.

## Manual Testing

### Via Terminal

```bash
# Connect via API tool (if available)
ros-api-client --host 192.168.1.1 --user admin --password pass

# Run command
/system/identity/print
```

### Via Python (without this project)

```python
from librouteros import connect

api = connect(host='192.168.1.1', username='admin', password='password')
identity = list(api.path('/system/identity'))
print(identity)
api.close()
```

## Troubleshooting

### Error: "cannot connect"

1. Verify that API is enabled:
   ```bash
   /ip service print
   ```

2. Check firewall:
   ```bash
   /ip firewall filter print where dst-port=8728
   ```

### Error: "access denied"

- Check user permissions:
  ```bash
  /user print detail
  ```

### Error: "timeout"

- Increase timeout in configurations
- Check network latency
- Check router load

## References

- [RouterOS API Documentation](https://help.mikrotik.com/docs/display/ROS/API)
- [librouteros GitHub](https://github.com/luqasz/librouteros)
- [RouterOS Manual](https://help.mikrotik.com/docs/display/ROS/First+Time+Configuration)
