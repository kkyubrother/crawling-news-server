import socket
import ipaddress
import logging
from urllib.parse import urlparse, urljoin
from contextlib import contextmanager
import requests
from typing import Tuple, List

logger = logging.getLogger(__name__)

def is_ip_public(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved)
    except ValueError:
        return False

def validate_hostname_and_resolve(hostname: str) -> str:
    """
    Validates hostname, resolves IP addresses, checks against SSRF rules,
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
            raise ValueError(f"Hostname {hostname} resolved to restricted IP: {ip_str}")

    return addr_info[0][4][0]

def is_safe_url(url: str) -> bool:
    """
    Check if a given URL targets public IP addresses only and uses http/https.
    Blocks private IP addresses, loopback, link-local, multicast, etc.
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

@contextmanager
def pinned_dns(hostname: str, pinned_ip: str):
    orig_getaddrinfo = socket.getaddrinfo

    def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host and host.lower() == hostname.lower():
            return orig_getaddrinfo(pinned_ip, port, family, type, proto, flags)
        return orig_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = custom_getaddrinfo
    try:
        yield
    finally:
        socket.getaddrinfo = orig_getaddrinfo


def _request_get_with_redirect_check(url: str, headers: dict = None, timeout: int = 10, verify: bool = True, max_redirects: int = 5) -> requests.Response:
    current_url = url
    for _ in range(max_redirects):
        parsed = urlparse(current_url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

        hostname = parsed.hostname
        pinned_ip = validate_hostname_and_resolve(hostname)

        with pinned_dns(hostname, pinned_ip):
            response = requests.get(current_url, headers=headers, timeout=timeout, verify=verify, allow_redirects=False)

        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get('location')
            if not location:
                break
            current_url = urljoin(current_url, location)
        else:
            return response

    parsed = urlparse(current_url)
    hostname = parsed.hostname
    pinned_ip = validate_hostname_and_resolve(hostname)
    with pinned_dns(hostname, pinned_ip):
        return requests.get(current_url, headers=headers, timeout=timeout, verify=verify, allow_redirects=False)


def safe_request_get(url: str, headers: dict = None, timeout: int = 10) -> Tuple[requests.Response, bool]:
    """
    Executes an HTTP GET request with SSRF check, DNS rebinding prevention, default timeout, manual redirect validation, and SSL fallback.
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
