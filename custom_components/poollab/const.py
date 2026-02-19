"""Constants for the Poollab integration."""

DOMAIN = "poollab"
DEFAULT_NAME = "Poollab"

# API
API_BASE_URL = "https://backend.labcom.cloud/graphql"
API_TIMEOUT = 30  # seconds

# API Throttling & Rate Limiting
MIN_TIME_BETWEEN_UPDATES = 60  # 1 minute - minimum time between API calls
MAX_API_RETRIES = 3  # maximum retry attempts for failed API calls
RETRY_BACKOFF_MULTIPLIER = 2  # exponential backoff multiplier (1s -> 2s -> 4s)
RATE_LIMIT_RETRY_WAIT = 60  # seconds to wait when API reports rate limit (429)

# Update intervals
SCAN_INTERVAL = 300  # 5 minutes - how often to update device data

# Attributes
ATTR_DEVICE_ID = "device_id"
ATTR_DEVICE_NAME = "device_name"
ATTR_LAST_UPDATE = "last_update"

# Sensor types
SENSOR_TYPE_PH = "ph"
SENSOR_TYPE_CL = "chlorine"  # General chlorine (backward compatibility)
SENSOR_TYPE_FREE_CL = "free_chlorine"  # Free/Active chlorine
SENSOR_TYPE_TOTAL_CL = "total_chlorine"  # Total chlorine
SENSOR_TYPE_COMBINED_CL = "combined_chlorine"  # Combined chlorine (calculated)
SENSOR_TYPE_TEMP = "temperature"
SENSOR_TYPE_ALK = "alkalinity"
SENSOR_TYPE_CYA = "cya"
SENSOR_TYPE_SALT = "salt"

# ActiveChlorine calculated values
SENSOR_TYPE_UNBOUND_CL = "unbound_chlorine"  # Free chlorine available for sanitization
SENSOR_TYPE_BOUND_CYA = "bound_to_cya"  # Chlorine bound to CYA

# Sensor configurations
SENSOR_CONFIGS = {
    SENSOR_TYPE_PH: {
        "name": "pH",
        "unit": None,
        "icon": "mdi:water-opacity",
        "precision": 2,
        "min": 0,
        "max": 14,
    },
    SENSOR_TYPE_CL: {
        "name": "Chlorine",
        "unit": "ppm",
        "icon": "mdi:water-check",
        "precision": 2,
        "min": 0,
        "max": 10,
    },
    SENSOR_TYPE_FREE_CL: {
        "name": "Free Chlorine",
        "unit": "ppm",
        "icon": "mdi:water-check",
        "precision": 2,
        "min": 0,
        "max": 10,
        "description": "Active chlorine available for sanitization",
    },
    SENSOR_TYPE_TOTAL_CL: {
        "name": "Total Chlorine",
        "unit": "ppm",
        "icon": "mdi:water-plus",
        "precision": 2,
        "min": 0,
        "max": 10,
        "description": "Total chlorine in the pool (free + combined)",
    },
    SENSOR_TYPE_COMBINED_CL: {
        "name": "Combined Chlorine",
        "unit": "ppm",
        "icon": "mdi:water-alert",
        "precision": 2,
        "min": 0,
        "max": 5,
        "description": "Chlorine bound to contaminants (chloramines)",
        "calculated": True,
    },
    SENSOR_TYPE_TEMP: {
        "name": "Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "precision": 1,
        "min": 0,
        "max": 50,
    },
    SENSOR_TYPE_ALK: {
        "name": "Alkalinity",
        "unit": "ppm",
        "icon": "mdi:beaker",
        "precision": 0,
        "min": 0,
        "max": 300,
    },
    SENSOR_TYPE_CYA: {
        "name": "Stabilizer (CYA)",
        "unit": "ppm",
        "icon": "mdi:shield-check",
        "precision": 0,
        "min": 0,
        "max": 200,
    },
    SENSOR_TYPE_SALT: {
        "name": "Salt Level",
        "unit": "ppm",
        "icon": "mdi:shaker",
        "precision": 0,
        "min": 0,
        "max": 3600,
    },
    SENSOR_TYPE_UNBOUND_CL: {
        "name": "Unbound Chlorine",
        "unit": "ppm",
        "icon": "mdi:water-check",
        "precision": 2,
        "min": 0,
        "max": 5,
        "description": "Free chlorine available for sanitization (calculated)",
        "calculated": True,
    },
    SENSOR_TYPE_BOUND_CYA: {
        "name": "Chlorine Bound to CYA",
        "unit": "ppm",
        "icon": "mdi:water-alert",
        "precision": 2,
        "min": 0,
        "max": 5,
        "description": "Chlorine bound to stabilizer (CYA)",
        "calculated": True,
    },
}
