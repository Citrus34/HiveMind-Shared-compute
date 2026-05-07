# src/network/discovery.py
import subprocess
import json
from typing import Dict, List, Optional
from pydantic import BaseModel
import psutil
import zmq.asyncio
import asyncio
from datetime import datetime

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class NodeResources(BaseModel):
    cpu_cores: int
    cpu_percent: float
    memory_total_gb: float
    memory_available_gb: float
    gpu_available: bool
    gpu_type: str = "none"          # "cuda", "mps", or "none"
    gpu_memory_gb: Optional[float] = None
    timestamp: str

class DiscoveredPeer(BaseModel):
    tailscale_ip: str
    hostname: str
    resources: NodeResources
    node_id: str

class HiveMindDiscovery:
    CONTROL_PORT = 4242

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.context = zmq.asyncio.Context()
        self.my_resources = self._get_local_resources()

    def _get_local_resources(self) -> NodeResources:
        """Cross-platform GPU detection (Windows NVIDIA CUDA + Mac Studio MPS)."""
        mem = psutil.virtual_memory()

        gpu_available = False
        gpu_type = "none"
        gpu_memory_gb: Optional[float] = None

        if TORCH_AVAILABLE:
            try:
                # Windows NVIDIA CUDA
                if torch.cuda.is_available():
                    gpu_available = True
                    gpu_type = "cuda"
                    gpu_memory_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
                # Apple Silicon MPS (Mac Studio)
                elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
                    gpu_available = True
                    gpu_type = "mps"
                    # MPS does not expose VRAM easily, so use system RAM as proxy
                    gpu_memory_gb = round(mem.total / (1024**3), 2)
            except Exception as e:
                print(f"[GPU Detection] Non-fatal torch error: {e}")

        return NodeResources(
            cpu_cores=psutil.cpu_count(logical=False) or 4,
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_total_gb=round(mem.total / (1024**3), 2),
            memory_available_gb=round(mem.available / (1024**3), 2),
            gpu_available=gpu_available,
            gpu_type=gpu_type,
            gpu_memory_gb=gpu_memory_gb,
            timestamp=datetime.utcnow().isoformat()
        )

    # === Keep the rest of your previous class exactly as-is ===
    # (get_tailscale_peers, advertise_and_handshake, discover_peers)
    # Paste the rest from the earlier Tailscale discovery version here if you haven't already

    def get_tailscale_peers(self) -> List[Dict]:
        """Core discovery: query Tailscale daemon directly."""
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            peers = []
            for peer_key, peer_data in data.get("Peer", {}).items():
                if peer_data.get("Online"):
                    ips = peer_data.get("TailscaleIPs", [])
                    if ips:
                        peers.append({
                            "tailscale_ip": ips[0],
                            "hostname": peer_data.get("Hostname", peer_key),
                            "node_id": peer_key  # unique Tailscale identifier
                        })
            return peers
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[Discovery] Tailscale query failed: {e}. Falling back to local only.")
            return []

    async def advertise_and_handshake(self, peer_ip: str) -> Optional[DiscoveredPeer]:
        """Basic advertisement + resource exchange via ZeroMQ REQ/REP."""
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(f"tcp://{peer_ip}:{self.CONTROL_PORT}")
        try:
            # Send our advertisement
            await socket.send_json({
                "type": "HIVEHAND_SHAKE",
                "node_id": self.node_id,
                "resources": self.my_resources.model_dump()
            })
            # Wait for response (timeout 2s)
            response = await asyncio.wait_for(socket.recv_json(), timeout=2.0)
            if response.get("type") == "HIVEHAND_ACK":
                return DiscoveredPeer(
                    tailscale_ip=peer_ip,
                    hostname=response.get("hostname", "unknown"),
                    resources=NodeResources(**response["resources"]),
                    node_id=response["node_id"]
                )
        except asyncio.TimeoutError:
            pass  # not a HiveMind node or offline
        finally:
            socket.close()
        return None

    async def discover_peers(self) -> List[DiscoveredPeer]:
        """Full discovery + advertisement loop (call periodically)."""
        peers = self.get_tailscale_peers()
        active_hivemind_peers = []
        for p in peers:
            discovered = await self.advertise_and_handshake(p["tailscale_ip"])
            if discovered:
                active_hivemind_peers.append(discovered)
        return active_hivemind_peers