import socket
import ipaddress
import logging
from urllib.parse import urlparse
import requests
from typing import Tuple

logger = logging.getLogger(__name__)

def is_safe_url(url: str) -> bool:
    """
    Check if a given URL targets public IP addresses only and uses http/https.
    Blocks private IP addresses, loopback, link-local, multicast, etc.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Disallow explicit localhost names
        if hostname.lower() in ('localhost', 'localhost.localdomain', 'loopback'):
            return False

        # Resolve hostname to IP addresses
        # getaddrinfo returns tuples: (family, type, proto, canonname, sockaddr)
        addr_info = socket.getaddrinfo(hostname, None)
        if not addr_info:
            return False

        for item in addr_info:
            ip_str = item[4][0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
                logger.warning(f"SSRF blocked: URL {url} resolved to non-public IP {ip_str}")
                return False

        return True
    except Exception as e:
        logger.warning(f"SSRF check failed for URL {url}: {e}")
        return False


def safe_request_get(url: str, headers: dict = None, timeout: int = 10) -> Tuple[requests.Response, bool]:
    """
    Executes an HTTP GET request with SSRF check, default timeout, and SSL fallback.

    1. Validates URL against SSRF rules.
    2. Tries request with SSL verification (verify=True).
    3. If SSLError or CertificateError occurs, falls back to verify=False and logs warning.

    Returns (response, ssl_warning_triggered).
    """
    if not is_safe_url(url):
        raise ValueError(f"URL {url} is unsafe or targets a restricted address (SSRF protection).")

    ssl_warning = False
    try:
        response = requests.get(url, headers=headers, timeout=timeout, verify=True)
        return response, ssl_warning
    except (requests.exceptions.SSLError, requests.exceptions.CertificateError) as ssl_err:
        logger.warning(f"SSL verification failed for {url}: {ssl_err}. Retrying with verify=False...")
        ssl_warning = True
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
        return response, ssl_warning
