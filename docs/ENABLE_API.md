# Enabling RouterOS API - Step by Step Guide

This guide explains how to enable the RouterOS API on your Mikrotik routers.

## Prerequisites

- Administrative access to Mikrotik router
- Connection via:
  - WinBox (Windows/Wine)
  - WebFig (web interface)
  - SSH/Telnet (terminal)

---

## Method 1: Via WinBox (Recommended)

### Step 1: Connect to Router
1. Open WinBox
2. Enter router IP or use MAC address
3. Enter username and password
4. Click "Connect"

### Step 2: Enable API Service
1. In left menu, go to **IP → Services**
2. Find `api` row in the list
3. Double click on `api`
4. Check **Enabled** checkbox (if not already active)
5. Verify **Port** is `8728` (default)
6. (Optional but recommended) In **Available From** field, enter the IP or network to connect from
   - Example: `192.168.1.0/24` for entire local network
   - Example: `10.0.0.50` for a single IP
7. Click **OK**

### Step 3: Verify
1. Return to **IP → Services** list
2. Verify `api` shows:
   - ✓ in Enabled column
   - Port: 8728
   - Available From: (your IP/network if set)

---

## Method 2: Via SSH/Terminal

### Step 1: Connect via SSH
```bash
ssh admin@192.168.1.1
```

### Step 2: Enable API
```bash
/ip service enable api
```

### Step 3: Verify Configuration
```bash
/ip service print
```

Example output:
```
 # NAME     PORT ADDRESS   CERTIFICATE
 0 telnet   23              
 1 ftp      21              
 2 www      80              
 3 ssh      22              
 4 api      8728           
 5 winbox   8291           
 6 api-ssl  8729
```

Verify that `api` is present and doesn't have an `X` in front.

### Step 4 (Optional): Limit Access by IP
```bash
/ip service set api address=192.168.1.0/24
```

Replace `192.168.1.0/24` with your network.

---

## Method 3: Via WebFig

### Step 1: Access WebFig
1. Open browser
2. Go to `http://ROUTER_IP` (e.g: http://192.168.1.1)
3. Login with username/password

### Step 2: Enable API
1. In left menu: **IP → Services**
2. Find `api` in the list
3. Click pencil icon (✎) to edit
4. Check **Enabled**
5. Set **Port** to `8728`
6. (Optional) Set **Available From** with your IP/network
7. Click **Apply**

---

## Recommended Secure Configuration

### 1. Create Dedicated Read-Only User

**Via Terminal:**
```bash
# Create read-only group (if not exists)
/user group add name=api-readonly policy=read,api

# Create dedicated user
/user add name=inventory-reader group=api-readonly password=SecurePassword123!

# Verify
/user print
```

**Via WinBox:**
1. **System → Users**
2. Click **+** (Add New)
3. Name: `inventory-reader`
4. Group: `read` (or `api-readonly` if created)
5. Password: enter secure password
6. Click **OK**

### 2. Limit Access by IP

**Via Terminal:**
```bash
# Limit API to specific IP only
/ip service set api address=10.0.0.50

# Limit API to a network
/ip service set api address=10.0.0.0/24

# Limit API to multiple IPs/networks (comma-separated)
/ip service set api address=10.0.0.50,192.168.1.0/24
```

**Via WinBox:**
1. **IP → Services**
2. Double click on `api`
3. Available From: `10.0.0.50` or `10.0.0.0/24`
4. Click **OK**

### 3. Configure Firewall

**Allow API only from specific IP:**
```bash
# Add firewall rule
/ip firewall filter add chain=input protocol=tcp dst-port=8728 \
  src-address=10.0.0.50 action=accept place-before=0 \
  comment="Allow API from inventory server"

# Block API from others
/ip firewall filter add chain=input protocol=tcp dst-port=8728 \
  action=drop comment="Block API from others"
```

### 4. (Optional) Use API-SSL

API-SSL uses encrypted connection on port 8729:

```bash
# Enable API-SSL
/ip service enable api-ssl

# Configure certificate (optional)
# If not configured, uses self-signed certificate
```

**Note:** `librouteros` supports standard API (8728). For API-SSL you need client modifications.

---

## Verify Connection

### Test 1: Telnet to API Port
```bash
telnet 192.168.1.1 8728
```

If you connect successfully, you'll see some strange characters (binary API response). 
Press `Ctrl+]` then `quit` to exit.

### Test 2: Python Test Script
```bash
cd /path/to/ubiquiti-automation
python3 examples/test-connection.py 192.168.1.1 admin password
```

Expected output:
```
Testing connection to 192.168.1.1...
✓ Connected successfully
Router Identity: MyRouter
System Information:
  Version: 6.49.6
  ...
```

### Test 3: Verify from RouterOS
```bash
/log print where topics~"api"
```

You'll see logs of API connections.

---

## Troubleshooting

### Error: "Connection Refused"

**Possible causes:**
1. API not enabled
2. Wrong port
3. Firewall blocks connection

**Solution:**
```bash
# Verify API is enabled
/ip service print

# Check firewall
/ip firewall filter print

# Verify if API is listening
/system resource print
```

### Error: "Authentication Failed"

**Causes:**
1. Wrong username/password
2. User doesn't have API permissions

**Solution:**
```bash
# Verify user
/user print detail where name=inventory-reader

# Verify group and policy
/user group print detail where name=read
```

### Error: "Timeout"

**Causes:**
1. Router unreachable
2. Timeout too short
3. Router overloaded

**Solution:**
- Verify connectivity: `ping 192.168.1.1`
- Increase timeout in `config.yaml`
- Reduce load on router

### Error: "Access Denied from IP"

**Cause:**
- Source IP not in `Available From`

**Solution:**
```bash
# Verify configuration
/ip service print detail

# Add your IP
/ip service set api address=CURRENT_IPS,YOUR_IP
```

---

## Best Practices Security

### ✅ DO (Do This)
- ✓ Use dedicated read-only user
- ✓ Limit access by IP (Available From)
- ✓ Use strong passwords (12+ characters)
- ✓ Configure firewall rules
- ✓ Monitor API logs regularly
- ✓ Disable API when not in use (insecure networks)
- ✓ Consider API-SSL for public networks

### ❌ DON'T (Don't Do This)
- ✗ Don't use `admin` user for API
- ✗ Don't leave API open to everyone (`0.0.0.0/0`)
- ✗ Don't use simple passwords
- ✗ Don't expose API on Internet without VPN
- ✗ Don't forget to update RouterOS

---

## Multi-Router Configuration

### Script to Enable API on Multiple Routers

```bash
#!/bin/bash
# enable-api-all.sh

ROUTERS=(
  "192.168.1.1"
  "192.168.1.2"
  "192.168.1.3"
)

USERNAME="admin"
PASSWORD="your-password"
ALLOWED_IP="10.0.0.50"

for ROUTER in "${ROUTERS[@]}"; do
  echo "Configuring $ROUTER..."
  
  sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no \
    $USERNAME@$ROUTER << EOF
/ip service enable api
/ip service set api address=$ALLOWED_IP
/log print where topics~"api"
exit
EOF
  
  echo "✓ $ROUTER configured"
  echo ""
done

echo "All routers configured!"
```

Usage:
```bash
chmod +x enable-api-all.sh
./enable-api-all.sh
```

---

## Monitoring API Access

### View API Connection Logs

```bash
# Last 20 API logs
/log print where topics~"api" count=20

# API logs from last hour
/log print where topics~"api" and time>=[/system clock get time]

# Filter by specific user
/log print where topics~"api" and message~"inventory-reader"
```

### Alert on Unauthorized Connections

```bash
# Create script that sends email on connections from unknown IPs
/system script add name=api-alert source={
  :local apiLog [/log find where topics~"api" and message~"failed"]
  :if ([:len $apiLog] > 0) do={
    /tool e-mail send to="admin@example.com" \
      subject="API Access Alert" \
      body="Unauthorized API access detected"
  }
}

# Execute script every 5 minutes
/system scheduler add name=api-check interval=5m \
  on-event=api-alert
```

---

## References

- [RouterOS API Manual](https://help.mikrotik.com/docs/display/ROS/API)
- [RouterOS Services](https://help.mikrotik.com/docs/display/ROS/Services)
- [librouteros Documentation](https://github.com/luqasz/librouteros)

---

## Complete Setup Checklist

- [ ] API enabled on port 8728
- [ ] Read-only user created (`inventory-reader`)
- [ ] Available From configured with secure IP
- [ ] Firewall rules configured (optional but recommended)
- [ ] Strong password set
- [ ] Connection test executed successfully
- [ ] API logs monitored

**Once the checklist is complete, you're ready to use the inventory system!**

## Multi-Router Configuration

### Script to Enable API on Multiple Routers

```bash
#!/bin/bash
# enable-api-all.sh

ROUTERS=(
  "192.168.1.1"
  "192.168.1.2"
  "192.168.1.3"
)

USERNAME="admin"
PASSWORD="your-password"
ALLOWED_IP="10.0.0.50"

for ROUTER in "${ROUTERS[@]}"; do
  echo "Configuring $ROUTER..."
  
  sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no \
    $USERNAME@$ROUTER << EOF
/ip service enable api
/ip service set api address=$ALLOWED_IP
/log print where topics~"api"
exit
EOF
  
  echo "✓ $ROUTER configured"
  echo ""
done

echo "All routers configured!"
```

Usage:
```bash
chmod +x enable-api-all.sh
./enable-api-all.sh
```

---

## Monitoring API Access

### View API Connection Logs

```bash
# Last 20 API logs
/log print where topics~"api" count=20

# API logs from the last hour
/log print where topics~"api" and time>=[/system clock get time]

# Filter by specific user
/log print where topics~"api" and message~"inventory-reader"
```

### Alert on Unauthorized Connections

```bash
# Create script that sends email on connections from unknown IPs
/system script add name=api-alert source={
  :local apiLog [/log find where topics~"api" and message~"failed"]
  :if ([:len $apiLog] > 0) do={
    /tool e-mail send to="admin@example.com" \
      subject="API Access Alert" \
      body="Unauthorized API access detected"
  }
}

# Run script every 5 minutes
/system scheduler add name=api-check interval=5m \
  on-event=api-alert
```

---

## References

- [RouterOS API Manual](https://help.mikrotik.com/docs/display/ROS/API)
- [RouterOS Services](https://help.mikrotik.com/docs/display/ROS/Services)
- [librouteros Documentation](https://github.com/luqasz/librouteros)

---

## Complete Setup Checklist

- [ ] API enabled on port 8728
- [ ] Read-only user created (`inventory-reader`)
- [ ] Available From configured with safe IP
- [ ] Firewall rules configured (optional but recommended)
- [ ] Strong password set
- [ ] Connection test performed successfully
- [ ] API logs monitored

**Once the checklist is complete, you're ready to use the inventory system!**
