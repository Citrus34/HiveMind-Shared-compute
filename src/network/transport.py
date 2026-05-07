# src/network/transport.py
import asyncio
import json
from typing import Dict, Optional
import zmq.asyncio
from pydantic import BaseModel
from datetime import datetime
import psutil

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from .discovery import NodeResources  # we now share the updated model

class HiveMindControlListener:
    """Control plane listener for handshake & resource advertisement.
    Runs on every node, listens on Tailnet port 4242."""
    
    CONTROL_PORT = 4242
    HANDSHAKE_TYPE = "HIVEHAND_SHAKE"
    ACK_TYPE = "HIVEHAND_ACK"

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{self.CONTROL_PORT}")  # Tailnet routes this
        self.my_resources = self._get_local_resources()
        print(f"[ControlListener] Started on port {self.CONTROL_PORT} (node: {node_id})")

    def _get_local_resources(self) -> NodeResources:
        """Cross-platform resource detection (Windows NVIDIA CUDA + Mac Studio MPS).
        Exactly matches discovery.py for perfect handshake consistency."""
        mem = psutil.virtual_memory()

        gpu_available = False
        gpu_type = "none"
        gpu_memory_gb: Optional[float] = None

        if TORCH_AVAILABLE:
            try:
                # Windows NVIDIA CUDA (your laptop)
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

    async def handle_handshake(self) -> None:
        """Main control loop – responds to discovery handshakes."""
        while True:
            try:
                message = await self.socket.recv_json()
                if message.get("type") == self.HANDSHAKE_TYPE:
                    # Send our resources back
                    response = {
                        "type": self.ACK_TYPE,
                        "node_id": self.node_id,
                        "hostname": self.node_id,  # can be richer later
                        "resources": self.my_resources.model_dump()
                    }
                    await self.socket.send_json(response)
                    print(f"[ControlListener] Handshake ACK sent to {message.get('node_id')}")
                else:
                    await self.socket.send_json({"type": "ERROR", "message": "unknown command"})
            except Exception as e:
                print(f"[ControlListener] Error: {e}")
                await asyncio.sleep(0.1)

    async def stop(self):
        """Graceful shutdown."""
        self.socket.close()
        self.context.term()
        print("[ControlListener] Stopped")