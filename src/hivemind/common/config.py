"""
Settings Management (Pydantic Settings)
Loads from environment variables (HIVEMIND_ prefix) or .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import socket

class Settings(BaseSettings):
    """Global HiveMind configuration."""

    # Host-specific (Studio Mac)
    host_name: str = "studio-mac"
    host_ip: Optional[str] = None
    host_port: int = 8765
    host_interface: str = "0.0.0.0"

    # Client-specific (works for remote Tailscale devices)
    remote_host: Optional[str] = None          # e.g. "studio-mac" (Tailscale MagicDNS)
    remote_port: int = 8765

    # General
    log_level: str = "INFO"
    heartbeat_interval: int = 5                # seconds between client heartbeats

    model_config = SettingsConfigDict(
        env_prefix="HIVEMIND_",
        env_file=".env",
        extra="ignore",          # ignore unknown env vars
    )

    def get_host_address(self) -> str:
        """Helper used by discovery and ZeroMQ layers."""
        if self.host_ip:
            return f"{self.host_ip}:{self.host_port}"
        return f"{self.host_name}:{self.host_port}"

def get_settings() -> Settings:
    """Singleton-style accessor used everywhere."""
    return Settings()