# src/hivemind/network/discovery.py
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
    gpu_type: str = "none"
    gpu_memory_gb: Optional[float] = None
    timestamp: str

class DiscoveredPeer(BaseModel):
    tailscale_ip: str
    hostname: str
    resources: NodeResources
    node_id: str
    last_seen: str = ""

class HiveMindDiscovery:
    def __init__(self, node_id: str, control_port: int = 4242):
        self.node_id = node_id
        self.control_port = control_port
        self.context = zmq.asyncio.Context()
        self.my_resources = self._get_local_resources()
        self.live_peers: Dict[str, DiscoveredPeer] = {}

    def _get_local_resources(self) -> NodeResources:
        mem = psutil.virtual_memory()
        gpu_available = False
        gpu_type = "none"
        gpu_memory_gb: Optional[float] = None

        if TORCH_AVAILABLE:
            try:
                if torch.cuda.is_available():
                    gpu_available = True
                    gpu_type = "cuda"
                    gpu_memory_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
                elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
                    gpu_available = True
                    gpu_type = "mps"
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

    def get_tailscale_peers(self) -> List[Dict]:
        try:
            result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            peers = []
            for peer_key, peer_data in data.get("Peer", {}).items():
                if peer_data.get("Online"):
                    ips = peer_data.get("TailscaleIPs", [])
                    if ips:
                        peers.append({
                            "tailscale_ip": ips[0],
                            "hostname": peer_data.get("Hostname", peer_key),
                            "node_id": peer_key
                        })
            return peers
        except Exception as e:
            print(f"[Discovery] Tailscale query failed: {e}")
            return []

    async def send_heartbeat(self, peer_ip: str, peer_id: str) -> bool:
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(f"tcp://{peer_ip}:{self.control_port}")
        try:
            await socket.send_json({
                "type": "HIVEHAND_HEARTBEAT",
                "node_id": self.node_id
            })
            response = await asyncio.wait_for(socket.recv_json(), timeout=1.5)
            if response.get("type") == "HIVEHAND_ACK":
                peer = DiscoveredPeer(
                    tailscale_ip=peer_ip,
                    hostname=response.get("hostname", "unknown"),
                    resources=NodeResources(**response["resources"]),
                    node_id=response["node_id"],
                    last_seen=datetime.utcnow().isoformat()
                )
                self.live_peers[peer.node_id] = peer
                return True
        except asyncio.TimeoutError:
            self.live_peers.pop(peer_id, None)
        finally:
            socket.close()
        return False

    async def discover_and_heartbeat(self) -> Dict[str, DiscoveredPeer]:
        peers = self.get_tailscale_peers()
        for p in peers:
            await self.send_heartbeat(p["tailscale_ip"], p["node_id"])
        return self.live_peers

    # Backward compatibility
    async def discover_peers(self) -> Dict[str, DiscoveredPeer]:
        return await self.discover_and_heartbeat()