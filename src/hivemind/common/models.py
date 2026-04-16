"""
Data Models (Pydantic v2)
All network messages and internal objects are defined here for type safety.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class DeviceType(str, Enum):
    MAC_APPLE_SILICON = "mac_apple"
    MAC_INTEL = "mac_intel"
    LINUX = "linux"
    WINDOWS = "windows"
    OTHER = "other"

class GpuType(str, Enum):
    METAL = "metal"
    CUDA = "cuda"
    NONE = "none"

class ResourceStats(BaseModel):
    """Real-time resource reporting from any client."""
    cpu_cores: int
    cpu_usage_percent: float
    memory_total_gb: float
    memory_available_gb: float
    gpu_type: GpuType = GpuType.NONE
    gpu_memory_gb: Optional[float] = None

class NodeInfo(BaseModel):
    """Information sent by clients when they register/heartbeat."""
    device_name: str
    device_type: DeviceType
    resources: ResourceStats
    tailscale_ip: Optional[str] = None
    version: str = "0.1.0"
    capabilities: List[str] = Field(default_factory=list)  # e.g. ["cpu", "gpu", "metal"]

class DiscoveryInfo(BaseModel):
    """Result returned by discover_hosts() – used by clients."""
    hostname: str
    ip: str
    port: int
    version: str = "unknown"

class Task(BaseModel):
    """Basic task definition (we will expand this heavily next)."""
    task_id: str
    task_type: str  # e.g. "cpu_benchmark", "matrix_multiply", "inference"
    payload: Dict[str, Any]
    timeout_seconds: int = 300