# HiveMind Shared Compute – Device Setup Guide (macOS, Windows & Linux)

**Purpose**: Set up Tailscale on every device so HiveMind nodes form a secure, global, bidirectional mesh. This lets any node send/receive processing packets (tasks, results, GPU/CPU sharing) using stable MagicDNS names or Tailscale IPs — no port forwarding, no public IPs, no NAT headaches.

**Why Tailscale?**  
It creates a WireGuard-based mesh VPN with automatic NAT traversal, end-to-end encryption, and zero-config discovery. Perfect for Phase 1 P2P networking in HiveMind. All inter-node pyzmq communication will bind to Tailscale interfaces.  
**Sources**: Official Tailscale architecture docs[](https://tailscale.com/kb/1151).

## 1. One-Time Tailnet Admin Setup (Do this first)

1. Go to [https://login.tailscale.com/admin](https://login.tailscale.com/admin) and create a free account (use the same Google/Apple/GitHub/Microsoft login on all devices).
2. **Enable MagicDNS** (required for human-readable hostnames):
   - Visit: https://login.tailscale.com/admin/dns
   - Toggle **Enable MagicDNS** → ON.
3. **Set up Access Control List (ACLs)** for HiveMind security (copy-paste this policy):
   ```json
   {
     "acls": [
       {
         "action": "accept",
         "src": ["tag:computenode"],
         "dst": ["tag:computenode:*"]
       }
     ],
     "ssh": [
       {
         "action": "accept",
         "src": ["autogroup:admin"],
         "dst": ["tag:computenode"],
         "users": ["root", "autogroup:nonroot"]
       }
     ]
   }

Save at: https://login.tailscale.com/admin/acls
This creates a full bidirectional mesh only between compute nodes.

Sources: Tailscale ACLs documentation and MagicDNS guide.
2. Device Setup – macOS (Studio Mac + MacBooks)
Tested on: macOS 12+ (Apple Silicon & Intel).

Install
Go to https://tailscale.com/download → “Download for macOS”.
Open the .pkg and follow the installer.

First Run & Login
Open Tailscale from Spotlight (Cmd + Space).
Click Log in → use the same account as above.
Allow the VPN configuration prompt.

Tag as Compute Node (critical for ACLs)
In the menu-bar Tailscale icon → Admin console → Devices.
Edit each device → Tags → add tag:computenode.

Enable Tailscale SSH (for remote management)Bash# In Terminal
tailscale set --ssh
CLI VerificationBash# Check status
tailscale status

# Your stable IP
tailscale ip -4

# Test bidirectional ping to other nodes
ping studio-mac
ping windows-laptop

Sources: Official macOS install guide.
3. Device Setup – Windows (Personal Laptop)
Tested on: Windows 10/11.

Install
Go to https://tailscale.com/download → “Download for Windows”.
Run the .exe.

First Run & Login
App opens automatically.
Click Log in → same account.
Allow VPN configuration.

Tag as Compute Node
Go to web admin console.
Edit the Windows device → add tag tag:computenode.

CLI Verification (PowerShell as Administrator)PowerShell# Check status
tailscale status

# Your stable IP
tailscale ip -4

# Test bidirectional ping (this fixes the "no such host" error you saw)
ping studio-mac

Fix for your earlier SSH issue (“No ED25519 host key…”):
Run once on the target Mac:
Bashtailscale set --ssh
Then on Windows:
PowerShelltailscale ssh --accept-risks=lose-ssh studio-mac
Future connections work automatically.
Source: Tailscale SSH troubleshooting.
4. Device Setup – Linux (Future Volunteer Servers / Raspberry Pi)

InstallBashcurl -fsSL https://tailscale.com/install.sh | sh
Login & Tag (use an auth key for headless setup)
In admin console → Settings → Auth keys → generate reusable key.
Bashsudo tailscale up --authkey=tskey-xxx --advertise-tags=tag:computenode
Enable SSH & VerifyBashsudo tailscale set --ssh
tailscale status
tailscale ip -4
ping studio-mac

Source: Linux install guide.
5. HiveMind Integration (How packets flow)
Once Tailscale is running:

Nodes discover peers via the discover_compute_peers() helper (we’ll add this in src/hivemind/networking/tailscale.py).
pyzmq sockets bind to the Tailscale IP (e.g. tcp://100.x.x.x:5555).
All task/result packets travel encrypted over the mesh.

Next code step (add to your node startup):
Pythonfrom hivemind.networking.tailscale import get_tailscale_ip, discover_compute_peers
ts_ip = get_tailscale_ip()
if ts_ip:
    socket.bind(f"tcp://{ts_ip}:5555")
6. Troubleshooting

“no such host” → Use exact MagicDNS name from tailscale status.
Host key verification failed → Run the --accept-risks flag once (see Windows section).
Ping works but pyzmq fails → Check firewall allows traffic on your chosen port (Tailscale ACLs already permit it).
Device not online → Run tailscale up again.

7. Volunteer Onboarding (Future Global Scale)
Share this one-liner with volunteers:
“Install Tailscale → join our tailnet with this auth key → run tailscale up --advertise-tags=tag:computenode → done. Your GPU/CPU is now part of HiveMind.”

How to update your repo:

Open Mac _Windows_Setup.md in your editor.
Replace everything with the markdown above.
Commit with message: “docs: full Tailscale mesh setup guide for all platforms + HiveMind integration”.
(Optional) Update README.md Quick Start to link: See [Mac _Windows_Setup.md](./Mac _Windows_Setup.md) for Tailscale networking.

This guide is now self-contained, educational, and directly advances your shared-compute architecture. It teaches volunteers exactly how the barrier to high-end distributed processing is removed.
Documented Sources (all official as of April 2026):

Tailscale core docs: https://tailscale.com/kb (installation, ACLs, MagicDNS, SSH).
Your repo’s current Mac _Windows_Setup.md (raw): https://raw.githubusercontent.com/Citrus34/HiveMind-Shared-compute/main/Mac%20_Windows_Setup.md.
HiveMind project context: https://github.com/Citrus34/HiveMind-Shared-compute (README + pyproject.toml).

Let me know when you’ve pushed this — next we can generate the tailscale.py helper and update the node code together. We’re building the global layer!
