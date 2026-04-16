# HiveMind Shared Compute – Easy Tailscale Setup Guide  
*(macOS, Windows & Linux – For Anyone)*

**Welcome!**  
This guide turns your devices (and future volunteer computers) into a secure, global network where HiveMind can send and receive processing packets (tasks, results, GPU/CPU sharing) with zero port-forwarding or NAT problems.  

Tailscale creates a private mesh network using WireGuard. Every device gets a permanent name (like `studio-mac`) and a stable IP (like `100.64.x.x`). Your pyzmq sockets will simply talk over this mesh.

**Why this matters for HiveMind**  
Your current local discovery (zeroconf) works only on the same Wi-Fi. Tailscale removes the barrier so volunteers anywhere in the world can join and share high-end computing power.

**Time required**: 10–15 minutes per device.

## 1. One-Time Tailnet Admin Setup (Do This First)

1. Open your browser and go to [https://login.tailscale.com/admin](https://login.tailscale.com/admin).  
   Sign up / log in with the **same account** you will use on every device (Google, Apple, GitHub, or Microsoft works best).

2. **Enable MagicDNS** (this gives every device a readable name):  
   - Click **DNS** on the left menu.  
   - Toggle **Enable MagicDNS** → **ON**.  
   You’ll now see names like `studio-mac.your-tailnet.ts.net`.

3. **Set Access Control (ACLs)** so only compute nodes can talk to each other:  
   - Click **Access Controls** on the left.  
   - Replace everything with the code below, then click **Save**.  
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
This creates a secure bidirectional mesh for HiveMind packet passing.
Sources: Official Tailscale ACLs and MagicDNS documentation (https://tailscale.com/kb/1018/acls, https://tailscale.com/kb/1081/magicdns).
2. Device Setup – macOS

Go to https://tailscale.com/download → click Download for macOS.
Open the downloaded .pkg file and follow the installer.
Open Tailscale from Spotlight (press Cmd + Space, type “Tailscale”).
Click Log in and use the same account. Allow the VPN prompt.
Tag the device (important!):
Click the Tailscale icon in the menu bar → Admin console.
In Devices list, click the three dots next to your Mac → Edit → Tags → type tag:computenode → Save.

Enable SSH (for remote help):
Open Terminal and run:Bashtailscale set --ssh
Test it:Bashtailscale status
tailscale ip -4          # shows your stable IP
ping studio-mac          # should reply!

3. Device Setup – Windows

Go to https://tailscale.com/download → Download for Windows.
Run the .exe installer.
The app opens automatically → click Log in with the same account.
Tag the device: Use the web admin console (same as macOS step 5) and add tag:computenode.
Test it (open PowerShell as Administrator):PowerShelltailscale status
tailscale ip -4
ping studio-mac

4. Device Setup – Linux (Volunteer Servers or Raspberry Pi)

Open a terminal and run:Bashcurl -fsSL https://tailscale.com/install.sh | sh
Log in with an auth key (easiest for servers):
In admin console → Settings → Auth keys → Generate a reusable key.
Run:
Bashsudo tailscale up --authkey=tskey-XXXXXXXXXXXXXXXX --advertise-tags=tag:computenode
Enable SSH:Bashsudo tailscale set --ssh
Test:Bashtailscale status
ping studio-mac

5. HiveMind Integration (How Packets Flow)
Once Tailscale is on, your Python code can use the mesh automatically.
We will add a small helper file soon (src/hivemind/networking/tailscale.py), but for now you can test with this snippet in your node startup code:
Pythonimport subprocess
import json

def get_tailscale_ip():
    try:
        result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return None

ts_ip = get_tailscale_ip()
if ts_ip:
    print(f"✅ HiveMind using Tailscale IP: {ts_ip}")
    # Your pyzmq socket will bind here instead of 0.0.0.0
6. Common Problems & Solutions 
Problem 1: “no such host” when pinging
→ Solution: Use the exact name shown in tailscale status (usually short name like studio-mac). MagicDNS is case-sensitive.

Problem 2: “No ED25519 host key… Host key verification failed” (SSH error)
→ On the target Mac run: tailscale set --ssh
→ Then on Windows: tailscale ssh --accept-risks=lose-ssh studio-mac
(The key will be remembered forever after.)

Problem 3: Device shows “offline”
→ Run tailscale up again on that device. Make sure Tailscale app is running (on macOS/Windows).

Problem 4: Can’t see other devices
→ Double-check every device has the tag tag:computenode.
→ Restart Tailscale on all machines.

Problem 5: Windows firewall blocks pyzmq
→ Windows Defender Firewall → Allow an app → add Python.exe (or your HiveMind executable).

Problem 6: “Tailscale not found” in terminal
→ macOS: restart Terminal or run source ~/.zshrc
→ Windows: restart PowerShell after install.

Problem 7: Volunteer can’t join (headless setup)
→ Give them a reusable auth key from the admin console and the one-line command from section 4.

Problem 8: Slow connections
→ Tailscale will automatically use direct WireGuard tunnels. If it uses a relay (DERP), it’s still encrypted and works — just slightly slower.

Problem 9: Forgetting the tailnet
→ On any device run tailscale logout then log in again with the same account.

Problem 10: ACLs not working
→ Double-check the JSON policy was saved correctly (copy-paste exactly).
7. Volunteer Onboarding (Future Global Scale)

Send volunteers this simple message:
“1. Download Tailscale from https://tailscale.com/download

2. Log in with this link: [your tailnet invite link]

3. Run this command in terminal/PowerShell:
tailscale up --advertise-tags=tag:computenode

That’s it! Your computer is now part of HiveMind’s shared compute mesh.”
7. Volunteer Onboarding (Future Global Scale)
