import requests
import logging
from datetime import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pytz

class Appointment:
    """Represents a Global Entry appointment slot"""
    def __init__(self, location_id: str, start_timestamp: str, end_timestamp: str, duration: int = 15):
        self.location_id = location_id
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.duration = duration
        self.est_tz = pytz.timezone('America/New_York')

    @property
    def date(self):
        utc_time = datetime.strptime(self.start_timestamp, '%Y-%m-%dT%H:%M')
        est_time = pytz.UTC.localize(utc_time).astimezone(self.est_tz)
        return est_time.strftime('%Y-%m-%d')

    @property
    def time(self):
        utc_time = datetime.strptime(self.start_timestamp, '%Y-%m-%dT%H:%M')
        est_time = pytz.UTC.localize(utc_time).astimezone(self.est_tz)
        return est_time.strftime('%I:%M %p EST')  # 12-hour format with AM/PM and EST indicator

class GlobalEntrySlotChecker:
    BASE_URL = "https://ttp.cbp.dhs.gov/schedulerapi/slots"

    def __init__(self, location_ids, date_start, date_end):
        self.location_ids = location_ids
        self.date_start = date_start
        self.date_end = date_end
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initialized with date range: {date_start} to {date_end}")

        # Store last seen slots to prevent duplicate notifications
        self.last_seen_slots = {}

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

    def _slots_changed(self, location_id: str, new_slots: list) -> bool:
        """
        Compare new slots with last seen slots to determine if notification should be sent
        Returns True if slots have changed or if this is the first check
        """
        if not new_slots:
            # If no new slots and we didn't have any before, no change
            return bool(self.last_seen_slots.get(location_id))

        # Get the first slot since we only care about the earliest date
        new_slot = new_slots[0]
        last_slot = self.last_seen_slots.get(location_id)

        # If we have no last seen slots, or if the slots are different
        if not last_slot:
            self.last_seen_slots[location_id] = new_slot
            return True

        # Compare date and times
        has_changed = (
            new_slot['date'] != last_slot['date'] or 
            new_slot['times'] != last_slot['times']
        )

        if has_changed:
            self.last_seen_slots[location_id] = new_slot
            self.logger.info(f"Slots changed for location {location_id}")

        return has_changed

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
                url = f"{self.BASE_URL}?orderBy=soonest&locationId={location_id}&minimum=1"

                response = self._make_request(url)
                if not response:
                    continue

                if response.status_code == 200:
                    slots = response.json()
                    self.logger.info(f"Found {len(slots)} slots for location {location_id}")
                    processed_slots = self._process_slots(slots, location_id)

                    # Only add slots to available_slots if they've changed
                    if processed_slots and self._slots_changed(location_id, processed_slots):
                        available_slots.extend(processed_slots)

                elif response.status_code == 403:
                    self.logger.warning("Session expired, refreshing...")
                    if self._refresh_session():
                        response = self._make_request(url)
                        if response and response.status_code == 200:
                            slots = response.json()
                            self.logger.info(f"Found {len(slots)} slots for location {location_id}")
                            processed_slots = self._process_slots(slots, location_id)
                            if processed_slots and self._slots_changed(location_id, processed_slots):
                                available_slots.extend(processed_slots)
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
        """Process and format available slots, returning only the earliest date"""
        processed_slots = []
        slots_by_date = {}
        location_names = {
            '5140': 'JFK International Airport',
            '14321': 'Charlotte-Douglas International Airport',
            '5182': 'Daniel K. Inouye International Airport',
            # Add more locations as needed
        }
        location_name = location_names.get(location_id, f'Location {location_id}')

        self.logger.info(f"Processing slots for {location_name}")

        # Group slots by date
        for slot_data in slots:
            try:
                appointment = Appointment(
                    location_id=location_id,
                    start_timestamp=slot_data['startTimestamp'],
                    end_timestamp=slot_data.get('endTimestamp', ''),
                    duration=slot_data.get('duration', 15)
                )

                # Group slots by date
                if appointment.date not in slots_by_date:
                    slots_by_date[appointment.date] = []
                slots_by_date[appointment.date].append(appointment.time)

                self.logger.debug(f"Added slot for {location_name} on {appointment.date} at {appointment.time}")

            except Exception as e:
                self.logger.error(f"Error processing slot {slot_data}: {str(e)}")

        if slots_by_date:
            # Get the earliest date
            earliest_date = min(slots_by_date.keys())
            times = sorted(slots_by_date[earliest_date])  # Sort times chronologically

            slot_info = {
                'location': location_id,
                'date': earliest_date,
                'times': times,
                'location_name': location_name
            }
            self.logger.info(f"Found {len(times)} slots at {location_name} on {earliest_date}: {', '.join(times)}")
            processed_slots.append(slot_info)
        else:
            self.logger.info(f"No available slots found at {location_name}")

        return processed_slots

    def get_test_slot(self):
        """Generate a test slot for verification purposes"""
        location_id = self.location_ids[0]
        location_names = {
            '5140': 'JFK International Airport',
            '14321': 'Charlotte-Douglas International Airport',
            '5182': 'Daniel K. Inouye International Airport',
            # Add more locations as needed
        }
        location_name = location_names.get(location_id, f'Location {location_id}')

        # Get current time in EST
        est_tz = pytz.timezone('America/New_York')
        current_time = datetime.now(est_tz)

        test_slot = {
            'location': location_id,
            'location_name': location_name,
            'date': current_time.strftime('%Y-%m-%d'),
            'time': current_time.strftime('%I:%M %p EST'),  # 12-hour format with AM/PM and EST indicator
            'timestamp': current_time.strftime('%Y-%m-%dT%H:%M')
        }
        self.logger.info(f"Generated test slot: {test_slot}")
        return [test_slot]