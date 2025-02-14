import requests
import logging
from datetime import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class Appointment:
    """Represents a Global Entry appointment slot"""
    def __init__(self, location_id: str, start_timestamp: str, end_timestamp: str, duration: int = 15):
        self.location_id = location_id
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.duration = duration

    @property
    def date(self):
        return datetime.strptime(self.start_timestamp, '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d')

    @property
    def time(self):
        return datetime.strptime(self.start_timestamp, '%Y-%m-%dT%H:%M').strftime('%H:%M')

class GlobalEntrySlotChecker:
    BASE_URL = "https://ttp.cbp.dhs.gov/schedulerapi/slots"

    def __init__(self, location_ids, date_start, date_end):
        self.location_ids = location_ids
        self.date_start = date_start
        self.date_end = date_end
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initialized with date range: {date_start} to {date_end}")

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # retry on these status codes
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def check_slots(self):
        """Check for available appointment slots"""
        available_slots = []

        # First refresh the session before checking slots
        if not self._refresh_session():
            self.logger.error("Failed to refresh session, cannot proceed with slot check")
            return []

        for location_id in self.location_ids:
            try:
                self.logger.info(f"Checking slots for location {location_id}")
                url = f"{self.BASE_URL}?orderBy=soonest&limit=1&locationId={location_id}&minimum=1"

                response = self._make_request(url)
                if not response:
                    continue

                if response.status_code == 200:
                    slots = response.json()
                    self.logger.info(f"Found {len(slots)} slots for location {location_id}")
                    available_slots.extend(self._process_slots(slots, location_id))
                elif response.status_code == 403:
                    self.logger.warning("Session expired, refreshing...")
                    if self._refresh_session():
                        response = self._make_request(url)
                        if response and response.status_code == 200:
                            slots = response.json()
                            self.logger.info(f"Found {len(slots)} slots for location {location_id}")
                            available_slots.extend(self._process_slots(slots, location_id))
                else:
                    self._handle_error_response(response, location_id)

                # Add delay between requests to avoid rate limiting
                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error checking slots for location {location_id}: {str(e)}")

        return available_slots

    def _refresh_session(self):
        """Refresh the session by visiting the main scheduling page"""
        try:
            self.logger.info("Refreshing session...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }

            response = self.session.get(
                'https://ttp.cbp.dhs.gov/schedulerui/schedule-interview/location',
                params={
                    'lang': 'en',
                    'vo': 'true',
                    'returnUrl': 'ttpui/home',
                    'service': 'up'
                },
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                self.logger.info("Session refreshed successfully")
                self.logger.debug(f"New cookies: {dict(self.session.cookies)}")
                return True
            else:
                self.logger.warning(f"Failed to refresh session. Status code: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Error refreshing session: {str(e)}")
            return False

    def _make_request(self, url):
        """Make HTTP request to the scheduler API with proper headers"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://ttp.cbp.dhs.gov/schedulerui/schedule-interview/location?lang=en&vo=true&returnUrl=ttpui/home&service=up',
            'Origin': 'https://ttp.cbp.dhs.gov',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

        try:
            self.logger.debug(f"Making request to URL: {url}")
            self.logger.debug(f"Current cookies: {dict(self.session.cookies)}")

            response = self.session.get(url, headers=headers, timeout=30)

            self.logger.debug(f"Response status code: {response.status_code}")
            self.logger.debug(f"Response cookies: {dict(response.cookies)}")

            if response.status_code != 200:
                self.logger.debug(f"Response content: {response.text[:500]}")

            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None

    def _handle_error_response(self, response, location_id):
        """Handle various error responses from the API"""
        if not response:
            self.logger.error(f"No response received for location {location_id}")
            return

        try:
            error_content = response.json()
            error_msg = f"API Error for location {location_id}: {error_content}"
        except:
            error_msg = f"Unexpected response for location {location_id}"

        self.logger.warning(error_msg)
        self.logger.debug(f"Response status: {response.status_code}")
        self.logger.debug(f"Response headers: {dict(response.headers)}")
        self.logger.debug(f"Response content: {response.text}")

    def _process_slots(self, slots, location_id):
        """Process and format available slots"""
        processed_slots = []
        location_names = {
            '5140': 'JFK International Airport',
            '14321': 'Charlotte-Douglas International Airport'
            # Add more locations as needed
        }
        location_name = location_names.get(location_id, f'Location {location_id}')

        self.logger.info(f"Processing slots for {location_name}")

        for slot_data in slots:
            try:
                appointment = Appointment(
                    location_id=location_id,
                    start_timestamp=slot_data['startTimestamp'],
                    end_timestamp=slot_data.get('endTimestamp', ''),
                    duration=slot_data.get('duration', 15)
                )
                slot_info = {
                    'location': appointment.location_id,
                    'date': appointment.date,
                    'time': appointment.time,
                    'timestamp': appointment.start_timestamp
                }
                self.logger.info(f"Found slot at {location_name}: {appointment.date} at {appointment.time}")
                processed_slots.append(slot_info)
            except Exception as e:
                self.logger.error(f"Error processing slot {slot_data}: {str(e)}")

        if not processed_slots:
            self.logger.info(f"No available slots found at {location_name}")

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