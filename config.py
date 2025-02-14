import os
from datetime import datetime, timedelta

def load_config():
    """Load and validate configuration from environment variables"""

    # Use default location IDs if none provided
    default_locations = '14321'  # Charlotte-Douglas International Airport - 5501 Josh Birmingham Parkway Charlotte NC 28208
    location_ids = os.getenv('LOCATION_IDS', default_locations)

    now = datetime.now()
    config = {
        'LOCATION_IDS': [str(loc_id).strip() for loc_id in location_ids.split(',')],  # Ensure proper string formatting
        'DATE_START': now.strftime('%Y-%m-%d'),  # Just the date portion for API
        'DATE_END': (now + timedelta(days=365)).strftime('%Y-%m-%d'),  # Just the date portion for API
        'CHECK_INTERVAL': int(os.getenv('CHECK_INTERVAL', '900')),  # 15 minutes default
        'NTFY_TOPIC': os.getenv('NTFY_TOPIC', 'vu_alert')
    }

    # Validate required configuration
    if not config['LOCATION_IDS']:
        raise ValueError("LOCATION_IDS environment variable is empty or invalid")

    return config