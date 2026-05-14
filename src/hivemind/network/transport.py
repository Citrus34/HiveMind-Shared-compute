# src/hivemind/network/transport.py
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

from .discovery import NodeResources

class HiveMindControlListener:
    """Control plane listener for handshake, resource advertisement + heartbeats."""
    
    def __init__(self, node_id: str, control_port: int = 4242):
        self.node_id = node_id
        self.control_port = control_port
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{self.control_port}")
        self.my_resources = self._get_local_resources()
        print(f"[ControlListener] Started on port {self.control_port} (node: {node_id})")

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

    async def handle_handshake(self) -> None:
        """Main control loop – handles handshakes AND heartbeats."""
        while True:
            try:
                message = await self.socket.recv_json()
                msg_type = message.get("type")

                if msg_type in ("HIVEHAND_SHAKE", "HIVEHAND_HEARTBEAT"):
                    response = {
                        "type": "HIVEHAND_ACK",
                        "node_id": self.node_id,
                        "hostname": self.node_id,
                        "resources": self.my_resources.model_dump()
                    }
                    await self.socket.send_json(response)
                else:
                    await self.socket.send_json({"type": "ERROR", "message": "unknown command"})
            except Exception as e:
                print(f"[ControlListener] Error: {e}")
                await asyncio.sleep(0.1)

    async def stop(self):
        self.socket.close()
        self.context.term()
        print("[ControlListener] Stopped")