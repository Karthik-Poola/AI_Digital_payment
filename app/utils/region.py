"""
Region and currency detection utilities.
"""

from flask import request

# Mapping of regions to their default currency and symbol
REGION_CURRENCY_MAP = {
    "IN": {"currency": "INR", "symbol": "₹", "name": "India"},
    "US": {"currency": "USD", "symbol": "$", "name": "United States"},
    "GB": {"currency": "GBP", "symbol": "£", "name": "United Kingdom"},
    "EU": {"currency": "EUR", "symbol": "€", "name": "Europe"},
    "DE": {"currency": "EUR", "symbol": "€", "name": "Germany"},
    "FR": {"currency": "EUR", "symbol": "€", "name": "France"},
    "IT": {"currency": "EUR", "symbol": "€", "name": "Italy"},
    "ES": {"currency": "EUR", "symbol": "€", "name": "Spain"},
    "CA": {"currency": "CAD", "symbol": "C$", "name": "Canada"},
    "AU": {"currency": "AUD", "symbol": "A$", "name": "Australia"},
    "JP": {"currency": "JPY", "symbol": "¥", "name": "Japan"},
    "SG": {"currency": "SGD", "symbol": "S$", "name": "Singapore"},
    "HK": {"currency": "HKD", "symbol": "HK$", "name": "Hong Kong"},
    "BR": {"currency": "BRL", "symbol": "R$", "name": "Brazil"},
    "MX": {"currency": "MXN", "symbol": "$", "name": "Mexico"},
    "ZA": {"currency": "ZAR", "symbol": "R", "name": "South Africa"},
    "AE": {"currency": "AED", "symbol": "د.إ", "name": "United Arab Emirates"},
    "SA": {"currency": "SAR", "symbol": "﷼", "name": "Saudi Arabia"},
}

DEFAULT_REGION = "US"
DEFAULT_CURRENCY = "USD"


def detect_region_from_request():
    """
    Detect region from the incoming HTTP request.
    
    Tries to detect from:
    1. X-Forwarded-For header (contains client IP)
    2. Accept-Language header
    3. Custom X-Region header
    4. Falls back to default (US)
    """
    # Check for explicit region header (useful for mobile/frontend to pass)
    region = request.headers.get("X-Region")
    if region and region.upper() in REGION_CURRENCY_MAP:
        return region.upper()
    
    # Check Accept-Language header (e.g., "en-IN", "en-GB", "en-US")
    accept_language = request.headers.get("Accept-Language", "")
    if accept_language:
        # Parse the first language preference
        lang_parts = accept_language.split(",")[0].split("-")
        if len(lang_parts) > 1:
            country_code = lang_parts[1].upper()
            if country_code in REGION_CURRENCY_MAP:
                return country_code
    
    # Default to US if no region detected
    return DEFAULT_REGION


def get_currency_for_region(region_code):
    """
    Get the default currency code for a given region.
    
    Args:
        region_code: ISO 3166-1 alpha-2 country code (e.g., "IN", "US")
    
    Returns:
        Currency code (e.g., "INR", "USD")
    """
    region_code = region_code.upper() if region_code else DEFAULT_REGION
    region_info = REGION_CURRENCY_MAP.get(region_code, REGION_CURRENCY_MAP[DEFAULT_REGION])
    return region_info["currency"]


def get_currency_symbol(currency_code):
    """Get the symbol for a given currency code."""
    for region_info in REGION_CURRENCY_MAP.values():
        if region_info["currency"] == currency_code:
            return region_info["symbol"]
    # Fallback to currency code itself
    return currency_code


def get_region_name(region_code):
    """Get the display name for a region."""
    region_code = region_code.upper() if region_code else DEFAULT_REGION
    return REGION_CURRENCY_MAP.get(region_code, {}).get("name", region_code)


def format_currency(amount, currency_code, symbol=True):
    """
    Format an amount in the given currency.
    
    Args:
        amount: Numeric amount (float or int)
        currency_code: Currency code (e.g., "INR", "USD")
        symbol: If True, use symbol; if False, use currency code
    
    Returns:
        Formatted currency string
    """
    if symbol:
        currency_repr = get_currency_symbol(currency_code)
    else:
        currency_repr = currency_code
    
    # Format based on currency (different countries use different separators)
    if currency_code in ["JPY", "KRW"]:
        # No decimal places for these currencies
        return f"{currency_repr} {int(amount):,}"
    else:
        # Two decimal places for most currencies
        return f"{currency_repr} {amount:,.2f}"
