# Alternative MikroTik API Libraries

If you have issues with `librouteros`, you can try these alternatives:

## 1. routeros-api (recommended as alternative)

```bash
pip install routeros-api
```

### Usage example:

```python
import routeros_api

connection = routeros_api.RouterOsApiPool(
    '10.200.32.2',
    username='admin',
    password='your-password',
    plaintext_login=True  # For newer RouterOS
)

api = connection.get_api()

# Get identity
identity = api.get_resource('/system/identity').get()
print(identity)

# Get interfaces
interfaces = api.get_resource('/interface').get()
for iface in interfaces:
    print(iface['name'])

connection.disconnect()
```

## 2. Check RouterOS Version

The problem could be the RouterOS version. Some versions have API authentication issues.

Via SSH (add `-oHostKeyAlgorithms=+ssh-rsa` for old routers):
```bash
ssh -oHostKeyAlgorithms=+ssh-rsa admin@10.200.32.2
/system resource print
```

## 3. Authentication Problem Solutions

### A. Update RouterOS
- Download latest stable version from mikrotik.com
- Upgrade via WinBox: System → Packages

### B. Disable Challenge-Response
Via RouterOS terminal:
```
/user set admin disabled=no
```

### C. Create New API User
```
/user add name=api-user group=read password=SecurePass123
```

## 4. Test with routeros-api

Test script:

```python
#!/usr/bin/env python3
import routeros_api

try:
    conn = routeros_api.RouterOsApiPool(
        '10.200.32.2',
        username='admin',
        password='Beppe.08',
        plaintext_login=True,
        port=8728,
        use_ssl=False
    )
    
    api = conn.get_api()
    
    # Test
    identity = api.get_resource('/system/identity').get()
    print(f"Success! Router: {identity[0]['name']}")
    
    conn.disconnect()
except Exception as e:
    print(f"Error: {e}")
```

## 5. Debug RouterOS API

Via RouterOS terminal, enable logging:
```
/system logging add topics=api action=memory
/log print where topics~"api"
```
