"""
Security and URL Validation Utilities.
Blocks SSRF attacks (localhost, private RFC1918 IPs, link-local, cloud metadata services).
"""

import ipaddress
from typing import Optional
from urllib.parse import urlparse


def is_safe_url(url: Optional[str]) -> bool:
    """
    Checks if a URL is safe from SSRF attacks (no localhost, private RFC1918 IPs, loopback, or metadata services).
    """
    if not url or not isinstance(url, str):
        return True
    
    url = url.strip()
    if not url:
        return True
        
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False

        hostname_lower = hostname.lower()
        if hostname_lower in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal"):
            return False

        # Attempt to parse as IP address to check private / reserved ranges
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            # Not a numeric IP, hostname is a domain name
            pass

        return True
    except Exception:
        return False
