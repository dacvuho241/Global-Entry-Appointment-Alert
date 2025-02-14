import requests
import logging
from datetime import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        self._refresh_session()

        for location_id in self.location_ids:
            try:
                self.logger.info(f"Checking slots for location {location_id}")
                response = self._make_request(location_id)

                if response and response.status_code == 200:
                    slots = response.json()
                    self.logger.info(f"Found {len(slots)} slots for location {location_id}")
                    available_slots.extend(self._process_slots(slots, location_id))
                elif response and response.status_code == 403:
                    self.logger.warning("Session expired, refreshing...")
                    self._refresh_session()
                    response = self._make_request(location_id)  # Retry with new session
                    if response and response.status_code == 200:
                        slots = response.json()
                        self.logger.info(f"Found {len(slots)} slots for location {location_id}")
                        available_slots.extend(self._process_slots(slots, location_id))
                    else:
                        self._handle_error_response(response, location_id)
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
            response = self.session.get(
                'https://ttp.cbp.dhs.gov/schedulerui/schedule-interview/location',
                params={
                    'lang': 'en',
                    'vo': 'true',
                    'returnUrl': 'ttpui/home',
                    'service': 'up'
                },
                timeout=30
            )
            if response.status_code == 200:
                self.logger.info("Session refreshed successfully")
                self.logger.debug(f"New cookies: {dict(self.session.cookies)}")
            else:
                self.logger.warning(f"Failed to refresh session. Status code: {response.status_code}")

            # Log full response details for debugging
            self.logger.debug(f"Refresh response status: {response.status_code}")
            self.logger.debug(f"Refresh response headers: {dict(response.headers)}")
            self.logger.debug(f"Refresh response cookies: {dict(response.cookies)}")
        except Exception as e:
            self.logger.error(f"Error refreshing session: {str(e)}")

    def _make_request(self, location_id):
        """Make HTTP request to the scheduler API with proper headers"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://ttp.cbp.dhs.gov/schedulerui/schedule-interview/location?lang=en&vo=true&returnUrl=ttpui/home&service=up',
            'Origin': 'https://ttp.cbp.dhs.gov',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        try:
            # Construct the URL with path parameters
            url = f"{self.BASE_URL}/{location_id}/{self.date_start}/{self.date_end}"

            self.logger.debug(f"Making request to URL: {url}")
            self.logger.debug(f"Current cookies: {dict(self.session.cookies)}")

            response = self.session.get(url, headers=headers, timeout=30)

            # Log response details regardless of status code
            self.logger.debug(f"Response status code: {response.status_code}")
            self.logger.debug(f"Response cookies: {dict(response.cookies)}")
            self.logger.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code != 200:
                self.logger.debug(f"Response content: {response.text[:500]}")  # Log first 500 chars of response

            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for location {location_id}: {str(e)}")
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