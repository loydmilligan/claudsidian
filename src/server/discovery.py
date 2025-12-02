"""mDNS/Bonjour service discovery for Claudsidian.

This module provides local network service advertisement using mDNS (multicast DNS),
allowing Android and other clients to discover the Claudsidian server on the LAN
without knowing its IP address.

The service is advertised as:
- Service Type: _claudsidian._tcp.local.
- Service Name: Claudsidian Capture Server

Requires the zeroconf package for cross-platform mDNS support.
"""

import logging
import socket
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """Advertises Claudsidian server on the local network via mDNS.

    Uses Zeroconf (Python implementation of mDNS/DNS-SD) to advertise
    the service so that Android clients can discover it automatically.

    Example:
        >>> discovery = ServiceDiscovery(port=8765)
        >>> discovery.start()
        >>> # ... server runs ...
        >>> discovery.stop()
    """

    SERVICE_TYPE = "_claudsidian._tcp.local."
    SERVICE_NAME = "Claudsidian Capture Server"

    def __init__(self, port: int = 8765, host: Optional[str] = None):
        """Initialize service discovery.

        Args:
            port: Port the server is listening on
            host: Host address (if None, auto-detect local IP)
        """
        self._port = port
        self._host = host
        self._zeroconf = None
        self._service_info = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _get_local_ip(self) -> str:
        """Get the local IP address for LAN advertisement.

        Returns:
            Local IP address as string, or fallback to 127.0.0.1
        """
        try:
            # Create a socket to determine the local IP address
            # This connects to a public DNS server but doesn't actually
            # send any data - it just helps determine the local interface
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
            return ip
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return "127.0.0.1"

    def start(self) -> bool:
        """Start advertising the service on the local network.

        Returns:
            True if service advertisement started successfully, False otherwise
        """
        if self._running:
            logger.warning("Service discovery already running")
            return True

        try:
            from zeroconf import ServiceInfo, Zeroconf
        except ImportError:
            logger.warning(
                "zeroconf package not installed. "
                "Install with: pip install zeroconf"
            )
            return False

        try:
            # Determine IP address
            if self._host and self._host != "0.0.0.0":
                ip_addr = self._host
            else:
                ip_addr = self._get_local_ip()

            # Create service info
            self._service_info = ServiceInfo(
                self.SERVICE_TYPE,
                f"{self.SERVICE_NAME}.{self.SERVICE_TYPE}",
                addresses=[socket.inet_aton(ip_addr)],
                port=self._port,
                properties={
                    "version": "0.1.0",
                    "api": "/capture",
                    "path": "/",
                },
                server=f"claudsidian.local.",
            )

            # Start Zeroconf and register service
            self._zeroconf = Zeroconf()
            self._zeroconf.register_service(self._service_info)
            self._running = True

            logger.info(
                f"Service discovery started: {self.SERVICE_NAME} "
                f"at {ip_addr}:{self._port}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start service discovery: {e}")
            self._cleanup()
            return False

    def stop(self) -> None:
        """Stop advertising the service."""
        if not self._running:
            return

        logger.info("Stopping service discovery")
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up Zeroconf resources."""
        if self._zeroconf and self._service_info:
            try:
                self._zeroconf.unregister_service(self._service_info)
            except Exception as e:
                logger.warning(f"Error unregistering service: {e}")

        if self._zeroconf:
            try:
                self._zeroconf.close()
            except Exception as e:
                logger.warning(f"Error closing Zeroconf: {e}")

        self._zeroconf = None
        self._service_info = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if service discovery is running.

        Returns:
            True if advertising, False otherwise
        """
        return self._running

    @property
    def service_type(self) -> str:
        """Get the mDNS service type.

        Returns:
            Service type string
        """
        return self.SERVICE_TYPE


class ServiceBrowser:
    """Browse for Claudsidian servers on the local network.

    Used by Android/mobile clients to discover available servers.

    Example:
        >>> browser = ServiceBrowser()
        >>> servers = browser.discover(timeout=5.0)
        >>> for server in servers:
        ...     print(f"Found server at {server['host']}:{server['port']}")
    """

    def __init__(self):
        """Initialize service browser."""
        self._discovered_services: list[dict] = []
        self._lock = threading.Lock()

    def discover(self, timeout: float = 5.0) -> list[dict]:
        """Discover Claudsidian servers on the local network.

        Args:
            timeout: How long to search for servers in seconds

        Returns:
            List of discovered servers with host, port, and properties
        """
        try:
            from zeroconf import ServiceBrowser as ZeroconfBrowser
            from zeroconf import Zeroconf
        except ImportError:
            logger.warning("zeroconf package not installed")
            return []

        self._discovered_services = []

        try:
            zeroconf = Zeroconf()

            # Create a browser that calls our handler
            browser = ZeroconfBrowser(
                zeroconf,
                ServiceDiscovery.SERVICE_TYPE,
                self,
            )

            # Wait for discovery
            import time
            time.sleep(timeout)

            # Cleanup
            browser.cancel()
            zeroconf.close()

            with self._lock:
                return list(self._discovered_services)

        except Exception as e:
            logger.error(f"Error during service discovery: {e}")
            return []

    def add_service(self, zeroconf, service_type: str, name: str) -> None:
        """Handler called when a service is discovered.

        Args:
            zeroconf: Zeroconf instance
            service_type: Type of service discovered
            name: Name of the service
        """
        info = zeroconf.get_service_info(service_type, name)
        if info:
            with self._lock:
                self._discovered_services.append({
                    "name": name,
                    "host": socket.inet_ntoa(info.addresses[0]) if info.addresses else None,
                    "port": info.port,
                    "properties": {
                        k.decode() if isinstance(k, bytes) else k:
                        v.decode() if isinstance(v, bytes) else v
                        for k, v in info.properties.items()
                    } if info.properties else {},
                })
                logger.info(f"Discovered service: {name}")

    def remove_service(self, zeroconf, service_type: str, name: str) -> None:
        """Handler called when a service is removed.

        Args:
            zeroconf: Zeroconf instance
            service_type: Type of service
            name: Name of the service
        """
        with self._lock:
            self._discovered_services = [
                s for s in self._discovered_services if s["name"] != name
            ]
            logger.info(f"Service removed: {name}")

    def update_service(self, zeroconf, service_type: str, name: str) -> None:
        """Handler called when a service is updated.

        Args:
            zeroconf: Zeroconf instance
            service_type: Type of service
            name: Name of the service
        """
        # Re-add to get updated info
        self.remove_service(zeroconf, service_type, name)
        self.add_service(zeroconf, service_type, name)
