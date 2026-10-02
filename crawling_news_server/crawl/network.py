import socket
import ipaddress
import logging
from urllib.parse import urlparse, urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import parse_url
from urllib3.connection import HTTPSConnection, HTTPConnection
from typing import Tuple

logger = logging.getLogger(__name__)

def is_ip_public(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        # Use is_global to ensure it's globally routable (excludes private, loopback, link_local, CGNAT 100.64.0.0/10, reserved, etc.)
        return ip.is_global
    except ValueError:
        return False

def validate_hostname_and_resolve(hostname: str) -> str:
    """
    Validates hostname, resolves IP addresses, checks against SSRF rules (must be globally routable),
    and returns a validated public IP address.
    """
    if not hostname:
        raise ValueError("Empty or missing hostname")

    if hostname.lower() in ('localhost', 'localhost.localdomain', 'loopback'):
        raise ValueError(f"Restricted hostname: {hostname}")

    # Check if hostname itself is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if not is_ip_public(str(ip)):
            raise ValueError(f"IP {hostname} is restricted")
        return str(ip)
    except ValueError:
        pass

    addr_info = socket.getaddrinfo(hostname, None)
    if not addr_info:
        raise ValueError(f"Failed to resolve hostname: {hostname}")

    for item in addr_info:
        ip_str = item[4][0]
        if not is_ip_public(ip_str):
            raise ValueError(f"Hostname {hostname} resolved to non-global/restricted IP: {ip_str}")

    return addr_info[0][4][0]

def is_safe_url(url: str) -> bool:
    """
    Check if a given URL targets public globally routable IP addresses only and uses http/https.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        validate_hostname_and_resolve(parsed.hostname)
        return True
    except Exception as e:
        logger.warning(f"SSRF check failed for URL {url}: {e}")
        return False


class PinnedIPHTTPAdapter(HTTPAdapter):
    """
    Thread-safe HTTPAdapter that connects to a pre-validated pinned IP address
    while preserving TLS SNI and hostname verification.
    """
    def __init__(self, pinned_ip: str, *args, **kwargs):
        self.pinned_ip = pinned_ip
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['server_hostname'] = None
        super().init_poolmanager(*args, **kwargs)

    def get_connection(self, url, proxies=None):
        conn = super().get_connection(url, proxies=proxies)
        parsed = parse_url(url)
        # Preserve original domain name for TLS certificate hostname verification
        conn.assert_hostname = parsed.host
        # Override destination host for TCP socket connection
        conn.host = self.pinned_ip
        return conn


def _request_get_with_redirect_check(url: str, headers: dict = None, timeout: int = 10, verify: bool = True, max_redirects: int = 5) -> requests.Response:
    current_url = url
    for _ in range(max_redirects):
        parsed = urlparse(current_url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

        hostname = parsed.hostname
        pinned_ip = validate_hostname_and_resolve(hostname)

        session = requests.Session()
        adapter = PinnedIPHTTPAdapter(pinned_ip)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        response = session.get(current_url, headers=headers, timeout=timeout, verify=verify, allow_redirects=False)

        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get('location')
            if not location:
                return response
            current_url = urljoin(current_url, location)
        else:
            return response

    raise requests.exceptions.TooManyRedirects(f"Exceeded maximum redirects ({max_redirects}) for URL: {url}")


def safe_request_get(url: str, headers: dict = None, timeout: int = 10) -> Tuple[requests.Response, bool]:
    """
    Executes an HTTP GET request with SSRF check, thread-safe IP pinning, default timeout, manual redirect validation, and SSL fallback.
    """
    ssl_warning = False
    try:
        response = _request_get_with_redirect_check(url, headers=headers, timeout=timeout, verify=True)
        return response, ssl_warning
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as ssl_err:
        logger.warning(f"SSL verification/connection failed for {url}: {ssl_err}. Retrying with verify=False...")
        ssl_warning = True
        response = _request_get_with_redirect_check(url, headers=headers, timeout=timeout, verify=False)
        return response, ssl_warning
