import requests
import logging
from datetime import datetime

class GlobalEntrySlotChecker:
    BASE_URL = "https://ttp.cbp.dhs.gov/schedulerapi/slots"

    def __init__(self, location_ids, date_start, date_end):
        self.location_ids = location_ids
        self.date_start = date_start
        self.date_end = date_end
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initialized with date range: {date_start} to {date_end}")

    def check_slots(self):
        """Check for available appointment slots"""
        available_slots = []

        for location_id in self.location_ids:
            try:
                self.logger.info(f"Checking slots for location {location_id}")
                response = self._make_request(location_id)
                self.logger.debug(f"API Response status code: {response.status_code}")

                if response.status_code == 200:
                    slots = response.json()
                    self.logger.info(f"Found {len(slots)} slots for location {location_id}")
                    available_slots.extend(self._process_slots(slots, location_id))
                else:
                    try:
                        error_content = response.json()
                        self.logger.warning(f"API Error for location {location_id}: {error_content}")
                    except:
                        self.logger.warning(f"Unexpected status code {response.status_code} for location {location_id}")
            except Exception as e:
                self.logger.error(f"Error checking slots for location {location_id}: {str(e)}")

        return available_slots

    def _make_request(self, location_id):
        """Make HTTP request to the scheduler API"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        params = {
            'orderBy': 'soonest',
            'limit': 100,
            'locationId': location_id.strip(),
            'minimum': self.date_start,  # Using just date portion YYYY-MM-DD
            'maximum': self.date_end     # Using just date portion YYYY-MM-DD
        }

        self.logger.debug(f"Making request with params: {params}")
        return requests.get(self.BASE_URL, headers=headers, params=params)

    def _process_slots(self, slots, location_id):
        """Process and format available slots"""
        processed_slots = []

        for slot in slots:
            try:
                slot_time = datetime.strptime(slot['startTimestamp'], '%Y-%m-%dT%H:%M')
                processed_slots.append({
                    'location': location_id,
                    'date': slot_time.strftime('%Y-%m-%d'),
                    'time': slot_time.strftime('%H:%M'),
                    'timestamp': slot['startTimestamp']
                })
            except Exception as e:
                self.logger.error(f"Error processing slot {slot}: {str(e)}")

        return processed_slots

    def get_test_slot(self):
        """Generate a test slot for verification purposes"""
        test_slot = {
            'location': self.location_ids[0],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M'),
            'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M')
        }
        self.logger.info(f"Generated test slot: {test_slot}")
        return [test_slot]