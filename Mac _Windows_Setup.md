Complete Tailscale Setup Guide – macOS (Studio Mac + Both MacBooks)
Applies to Apple Silicon & Intel Macs (macOS 12+)

Download & Install (official Apple-native app)
Go to https://tailscale.com/download
Click “Download for macOS” → open the .pkg installer → follow prompts.
First Run & Login
Open Tailscale from Spotlight (Cmd + Space).
Click “Log in” → sign in with the same account you will use on all devices (Google/Apple/GitHub/Microsoft — pick one).
Allow the VPN configuration when prompted.

Enable MagicDNS (critical for HiveMind)
Open https://login.tailscale.com/admin/dns in a browser.
Toggle “Enable MagicDNS” to ON (this gives every device a permanent hostname like studio-mac).

Rename Devices (makes config human-readable)
In the Tailscale app menu bar icon → “Admin console” → Devices tab:
Click the three dots next to each device → “Edit” → set:
Studio Mac → studio-mac
Local MacBook Pro → macbook-local
Remote MacBook Pro → macbook-remote


CLI Commands (open Terminal and run)Bash# Check status
tailscale status

# Verify you can reach the host from any MacBook
ping studio-mac

# Show your Tailscale IP (should be 100.x.x.x)
tailscale ip -4

Sources: Official Tailscale macOS installation guide and MagicDNS documentation.
Complete Tailscale Setup Guide – Windows (Personal Laptop)
Tested on Windows 10/11

Download & Install
Go to https://tailscale.com/download
Click “Download for Windows” → run the .exe installer.
First Run & Login
The app will open automatically.
Click “Log in” → use the same account as the Macs.
Allow the VPN configuration when prompted.

Enable MagicDNS
Same as macOS: https://login.tailscale.com/admin/dns → toggle MagicDNS ON.
Rename the Windows Device
In the web admin console (Devices tab) → edit the Windows machine → name it windows-laptop.
CLI Commands (open PowerShell as Administrator)PowerShell# Check status
tailscale status

# Verify you can reach the Studio Mac
ping studio-mac

# Show your Tailscale IP
tailscale ip -4

Sources: Official Tailscale Windows installation guide and CLI reference.
Once Tailscale is Running on All Devices
From any device (including the Windows laptop), you should be able to:
Bashping studio-mac
If it responds, HiveMind’s hybrid discovery will work automatically.
In your client config (we’ll add this in the next files), remote devices will simply use:
YAMLremote_host: "studio-mac"