```
from hotspot_shield_utils import import_hotspot_codes, hotspot_disconnect, hotspot_connect_random

proxy_connected = False
while not proxy_connected:
    try:
        print("Disconnecting from the current proxy location...")
        hotspot_disconnect()
        print("Trying to connect to a new proxy location...")
        hotspot_connect_random(hotspot_codes)
        proxy_connected = True
    except Exception as exc:
        print(f"Failed to switch to a new proxy location, using Hotspot Shield CLI: {exc}")
        continue

```
which disconnnects from a current location and connects to some random location:
```
[RUNNER]: Disconnecting from the current proxy location...
[HOTSPOT_DISCONNECT]: Trying to disconnect...
[HOTSPOT_STATUS]: Checking status with hotspotshield status...
[HOTSPOT_STATUS]: hotspotshield status returned:
Client is running    : no
VPN connection state : disconnected

[HOTSPOT_DISCONNECT]: Successfully disconnected
[RUNNER]: Trying to connect to a new proxy location...
[HOTSPOT_STATUS]: Checking status with hotspotshield status...
[HOTSPOT_STATUS]: hotspotshield status returned:
Client is running    : yes
VPN connection state : connected
Connected location   : BN  (Brunei Darussalam)
Session uptime       : 0:02
Traffic per second   :    1.07 KiB down           0 B up
Traffic per session  :    3.70 KiB down      1.17 KiB up

[HOTSPOT_CONNECT_RANDOM]: Connected to BN successfully!
[RUNNER]: Successfully connected to a new proxy location
```

You can double check whether you are indeed connected by running `curl ipinfo.io`:

```
{
  "ip": "5.182.197.124",
  "city": "Bandar Seri Begawan",
  "region": "Brunei-Muara District",
  "country": "BN",
  "loc": "4.8903,114.9401",
  "org": "AS9009 M247 Ltd",
  "timezone": "Asia/Brunei",
  "readme": "https://ipinfo.io/missingauth"
}
```