"""
Geocoding utilities for converting addresses/zip codes to coordinates.
"""

import logging
import requests
from typing import Optional, Dict
from urllib.parse import quote

logger = logging.getLogger(__name__)


def geocode_zip_code(zip_code: str, country: str = "US") -> Optional[Dict[str, float]]:
    """
    Geocode a zip code to get latitude and longitude coordinates.
    
    Uses OpenStreetMap Nominatim API (free, no API key required).
    
    Args:
        zip_code: Zip code or postal code
        country: Country code (default: "US")
    
    Returns:
        Dictionary with 'lat', 'lon', 'zoom' keys, or None if geocoding fails
    """
    try:
        # Format query for Nominatim
        query = f"{zip_code}, {country}"
        
        # Nominatim API endpoint
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        
        headers = {
            "User-Agent": "CourseBuilder/1.0"  # Required by Nominatim
        }
        
        logger.info(f"Geocoding zip code: {zip_code}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            logger.warning(f"No results found for zip code: {zip_code}")
            return None
        
        result = data[0]
        lat = float(result["lat"])
        lon = float(result["lon"])
        
        logger.info(f"✓ Found location: {lat:.6f}, {lon:.6f}")
        logger.info(f"  Display name: {result.get('display_name', 'Unknown')}")
        
        return {
            "lat": lat,
            "lon": lon,
            "zoom": 15  # Default zoom level for zip code
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding request failed: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Failed to parse geocoding response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during geocoding: {e}")
        return None


def geocode_address(address: str) -> Optional[Dict[str, float]]:
    """
    Geocode an address to get latitude and longitude coordinates.
    
    Uses OpenStreetMap Nominatim API (free, no API key required).
    
    Args:
        address: Address string (e.g., "123 Main St, City, State")
    
    Returns:
        Dictionary with 'lat', 'lon', 'zoom' keys, or None if geocoding fails
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        
        headers = {
            "User-Agent": "CourseBuilder/1.0"
        }
        
        logger.info(f"Geocoding address: {address}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            logger.warning(f"No results found for address: {address}")
            return None
        
        result = data[0]
        lat = float(result["lat"])
        lon = float(result["lon"])
        
        logger.info(f"✓ Found location: {lat:.6f}, {lon:.6f}")
        logger.info(f"  Display name: {result.get('display_name', 'Unknown')}")
        
        return {
            "lat": lat,
            "lon": lon,
            "zoom": 15
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding request failed: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Failed to parse geocoding response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during geocoding: {e}")
        return None
