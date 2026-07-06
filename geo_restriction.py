"""
Geo-restriction middleware for HIPAA compliance

✅ HIPAA BAA OBTAINED from Microsoft Azure - US traffic now allowed!
This middleware can be enabled/disabled via BLOCK_US_TRAFFIC environment variable.

Author: PhysiologicPRISM
Created: 2026-01-10
Updated: 2026-01-11 (HIPAA BAA obtained, US blocking disabled)
"""

import os
import logging
from flask import request, jsonify, render_template

logger = logging.getLogger(__name__)

# ─── CONFIGURATION ─────────────────────────────────────────────────────

# Enable/disable geo-blocking via environment variable
# Default: false (HIPAA BAA obtained from Microsoft Azure)
GEO_BLOCKING_ENABLED = os.environ.get('BLOCK_US_TRAFFIC', 'false').lower() == 'true'

# Countries to block (currently none - HIPAA BAA obtained)
# Can be re-enabled for other regions if needed
BLOCKED_COUNTRIES = ['US', 'USA']

# Optional: Whitelist specific IPs (for testing, admin access, etc.)
WHITELISTED_IPS = os.environ.get('GEO_WHITELIST_IPS', '').split(',')
WHITELISTED_IPS = [ip.strip() for ip in WHITELISTED_IPS if ip.strip()]

# ─── FUNCTIONS ─────────────────────────────────────────────────────────

def get_client_ip(request):
    """
    Get the real client IP address, handling proxies and load balancers

    main.py wraps the WSGI app in ProxyFix(x_for=1, x_proto=1), which
    trusts exactly one proxy hop for X-Forwarded-For and rewrites
    request.remote_addr accordingly. Re-parsing the raw X-Forwarded-For/
    X-Real-IP headers directly here (as this used to) bypasses that
    trust boundary -- any direct client could set those headers itself
    to spoof its apparent IP for whitelist checks and audit logs.

    Args:
        request: Flask request object

    Returns:
        str: Client IP address
    """
    return request.remote_addr or request.environ.get('REMOTE_ADDR', 'unknown')


def get_client_country(request):
    """
    Detect the client's country from headers

    Checks multiple headers in order of reliability:
    1. CF-IPCountry (CloudFlare)
    2. X-AppEngine-Country (Google App Engine)
    3. X-Client-Geo-Location (some load balancers)

    Args:
        request: Flask request object

    Returns:
        str: Two-letter country code (e.g., 'US', 'IN') or None
    """
    # CloudFlare header (if using CloudFlare CDN)
    cf_country = request.headers.get('CF-IPCountry', '').upper()
    if cf_country and cf_country != 'XX':  # XX means unknown
        return cf_country

    # Google App Engine / Cloud Run header
    gae_country = request.headers.get('X-AppEngine-Country', '').upper()
    if gae_country and gae_country != 'XX':
        return gae_country

    # Generic geo-location header
    geo_country = request.headers.get('X-Client-Geo-Location', '').upper()
    if geo_country:
        return geo_country

    return None


def is_whitelisted_ip(ip_address):
    """
    Check if IP is whitelisted (for admin/testing access)

    Args:
        ip_address: Client IP address

    Returns:
        bool: True if whitelisted
    """
    if not WHITELISTED_IPS:
        return False

    return ip_address in WHITELISTED_IPS


def is_blocked_region(request):
    """
    Check if request is from a blocked region (US)

    Args:
        request: Flask request object

    Returns:
        tuple: (is_blocked: bool, country: str, ip: str)
    """
    client_ip = get_client_ip(request)

    # Check whitelist first (allows testing/admin access)
    if is_whitelisted_ip(client_ip):
        logger.info(f"✅ Whitelisted IP allowed: {client_ip}")
        return False, None, client_ip

    # Get country
    country = get_client_country(request)

    # If we can't determine country, allow by default (fail open)
    # This prevents false positives that could block legitimate users
    if not country:
        logger.debug(f"⚠️ Could not determine country for IP: {client_ip} - Allowing by default")
        return False, None, client_ip

    # Check if country is blocked
    is_blocked = country in BLOCKED_COUNTRIES

    return is_blocked, country, client_ip


def check_geo_restriction():
    """
    Main middleware function to check and enforce geo-restrictions

    Returns:
        Flask response or None (None means allow request to continue)
    """
    # Skip if geo-blocking is disabled
    if not GEO_BLOCKING_ENABLED:
        return None

    # Skip for specific paths (health checks, static files, etc.)
    skip_paths = [
        '/health',
        '/_ah/health',
        '/favicon.ico',
        '/robots.txt',
    ]

    if request.path in skip_paths or request.path.startswith('/static/'):
        return None

    # Check if region is blocked
    is_blocked, country, client_ip = is_blocked_region(request)

    if is_blocked:
        # Log the block
        logger.warning(f"🚫 BLOCKED ACCESS - Country: {country}, IP: {client_ip}, Path: {request.path}")

        # Return appropriate response based on request type
        if request.path.startswith('/api/'):
            # JSON response for API requests
            return jsonify({
                'ok': False,
                'error': 'service_unavailable_in_region',
                'message': 'This service is currently not available in your region.',
                'details': {
                    'blocked_country': country,
                    'reason': 'Regional restrictions apply',
                    'available_regions': 'United States, India, European Union, United Kingdom, Singapore, UAE, Australia, Canada',
                    'note': 'HIPAA BAA obtained for US operations'
                },
                'support_email': 'support@physiologicprism.com'
            }), 451  # 451 Unavailable For Legal Reasons (HTTP status)

        # HTML response for web requests
        try:
            return render_template('errors/geo_blocked.html',
                                 blocked_country=country,
                                 client_ip=client_ip), 451
        except Exception as e:
            logger.error(f"Error rendering geo_blocked template: {e}")
            # Fallback to simple text response
            return f"""
            <html>
            <head><title>Service Unavailable in Your Region</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 100px auto; text-align: center;">
                <h1>🌍 Service Not Available</h1>
                <p>This service is currently not available in your region.</p>
                <p><strong>Note:</strong> HIPAA BAA obtained - Service now available in US</p>
                <p>Available in: United States, India, EU, UK, Singapore, UAE, Australia, Canada</p>
                <hr>
                <p>Contact: <a href="mailto:support@physiologicprism.com">support@physiologicprism.com</a></p>
            </body>
            </html>
            """, 451

    # Allow request to continue
    return None


# ─── UTILITY FUNCTIONS ─────────────────────────────────────────────────

def get_geo_blocking_status():
    """
    Get current geo-blocking configuration status

    Returns:
        dict: Status information
    """
    return {
        'enabled': GEO_BLOCKING_ENABLED,
        'blocked_countries': BLOCKED_COUNTRIES,
        'whitelisted_ips': WHITELISTED_IPS if WHITELISTED_IPS else None,
        'environment_variable': 'BLOCK_US_TRAFFIC',
        'current_value': os.environ.get('BLOCK_US_TRAFFIC', 'true')
    }


if __name__ == '__main__':
    # Test/debug mode
    print("Geo-Restriction Configuration:")
    print(f"  Enabled: {GEO_BLOCKING_ENABLED}")
    print(f"  Blocked Countries: {BLOCKED_COUNTRIES}")
    print(f"  Whitelisted IPs: {WHITELISTED_IPS or 'None'}")
