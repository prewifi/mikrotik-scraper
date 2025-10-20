# FIX: RouterOS API Authentication Issue

## Problem Encountered

MD5 challenge-response authentication fails with "not logged in" error after first command.

```
!done
=ret=e17dce67dc67bc8a93375e00348a52e0  <-- Challenge received
!trap
=message=cannot log in  <-- Fails after hash response
```

## Cause

Mikrotik router uses MD5 challenge-response authentication (old protocol), but `librouteros` 3.4.1 doesn't complete the second step correctly.

## Solutions

### Solution 1: Update RouterOS (RECOMMENDED)

RouterOS 6.43+ supports safer plain-text authentication.

1. Via WinBox:
   - System → Packages → Check For Updates
   - Download & Install

2. Restart router

### Solution 2: Use RouterOS-API (Tested Alternative)

Install alternative library that works better:

```bash
pip install routeros-api
```

Modify `mikrotik-client.py` to use `routeros-api` instead of `librouteros`.

### Solution 3: Force Plain Login on RouterOS

On the router, disable MD5 challenge:

Via SSH:
```bash
ssh -oHostKeyAlgorithms=+ssh-rsa admin@10.200.32.2

# In RouterOS terminal:
/user set admin disabled=no
```

Via WinBox:
- System → Users
- Double-click on `admin`
- Make sure it's enabled

### Solution 4: Patch librouteros

If you can't update the router, apply this temporary patch:

```python
# In mikrotik-client.py, in connect() method:

from librouteros.login import plain
from librouteros import connect

def connect(self) -> bool:
    try:
        logger.info(f"Connecting to {self.host}:{self.port}...")
        
        # Force plain login
        self.api = connect(
            host=self.host,
            username=self.username,
            password=self.password,
            port=self.port,
            timeout=self.timeout,
            login_methods=(plain,)  # Force plain
        )
        
        logger.info(f"Successfully connected to {self.host}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return False
```

## Test the Solution

After applying a solution, test with:

```bash
python3 examples/test-connection.py 10.200.32.2 admin password
```

Expected output:
```
✓ Connected successfully
✓ Router Identity: YourRouterName
✓ System Information: ...
```

## If Nothing Works

1. Verify that API is enabled:
   ```
   /ip service print
   # Should show "api" with port 8728
   ```

2. Verify correct password via WinBox

3. Create new dedicated API user:
   ```
   /user add name=api-reader group=read password=NewSecurePassword
   ```

4. Test with new user

## Useful Links

- [librouteros Issues](https://github.com/luqasz/librouteros/issues)
- [RouterOS API Manual](https://help.mikrotik.com/docs/display/ROS/API)
- [routeros-api Alternative](https://pypi.org/project/routeros-api/)
