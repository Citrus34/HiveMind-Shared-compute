#Hybrid Service Discovery
#- mDNS (zeroconf) for local LAN devices
#- Direct config / Tailscale MagicDNS fallback for remote nodes


import time
import socket
import threading
from typing import Dict, List, Optional, Callable
import structlog
from zeroconf import (
    ServiceBrowser,
    ServiceInfo,
    ServiceListener,
    Zeroconf,
    IPVersion,
)

from .config import get_settings
from .models import DiscoveryInfo, NodeInfo
from .logging import get_logger

logger = get_logger(__name__)

SERVICE_TYPE = "_hivemind._tcp.local."
DEFAULT_PORT = 8765


class HiveMindListener(ServiceListener):
    """Listener for discovering HiveMind hosts via mDNS."""

    def __init__(self, on_host_discovered: Optional[Callable] = None):
        self.on_host_discovered = on_host_discovered or (lambda info: None)
        self.discovered_hosts: List[DiscoveryInfo] = []
        self._lock = threading.Lock()

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.info("Host left the network (mDNS)", service_name=name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.parsed_addresses(IPVersion.V4Only)]
            if addresses:
                disc_info = DiscoveryInfo(
                    hostname=info.server or name,
                    ip=addresses[0],
                    port=info.port or DEFAULT_PORT,
                    version=info.properties.get(b"version", b"unknown").decode(),
                )
                with self._lock:
                    self.discovered_hosts.append(disc_info)
                logger.info("Host discovered via mDNS", host=disc_info.hostname, ip=disc_info.ip, port=disc_info.port)
                self.on_host_discovered(disc_info)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass  # Not needed for our use case


def start_host_discovery() -> Zeroconf:
    """Host side: Advertise ourselves via mDNS (local LAN only)."""
    settings = get_settings()
    zc = Zeroconf(interfaces=["0.0.0.0"] if settings.host_interface == "0.0.0.0" else None)
    info = ServiceInfo(
        SERVICE_TYPE,
        f"{settings.host_name}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(settings.host_ip or "0.0.0.0")],
        port=settings.host_port or DEFAULT_PORT,
        properties={
            b"version": b"0.1.0",
            b"capabilities": b"cpu,gpu",
        },
    )
    zc.register_service(info)
    logger.info("Host advertising via mDNS", name=settings.host_name, port=info.port)
    return zc


def discover_hosts(timeout: float = 5.0) -> List[DiscoveryInfo]:
    """Client side: Try mDNS first, then fall back to config / Tailscale hostname."""
    settings = get_settings()
    hosts: List[DiscoveryInfo] = []

    # 1. Try mDNS (local LAN)
    zc = Zeroconf()
    listener = HiveMindListener()
    browser = ServiceBrowser(zc, SERVICE_TYPE, listener)
    time.sleep(timeout)  # Wait for responses
    with listener._lock:
        hosts.extend(listener.discovered_hosts)
    browser.cancel()
    zc.close()

    # 2. Fallback: Configured host (supports Tailscale MagicDNS hostname!)
    if not hosts and settings.remote_host:
        try:
            ip = socket.gethostbyname(settings.remote_host)  # Works for "studio-mac" or IP
            hosts.append(DiscoveryInfo(
                hostname=settings.remote_host,
                ip=ip,
                port=settings.remote_port or DEFAULT_PORT,
            ))
            logger.info("Using configured/Tailscale host", hostname=settings.remote_host, ip=ip)
        except socket.gaierror:
            logger.error("Could not resolve configured host", hostname=settings.remote_host)

    return hosts