import unittest
from unittest.mock import Mock, patch
import json
from datetime import datetime
from slot_checker import GlobalEntrySlotChecker, Appointment

class MockResponse:
    def __init__(self, status_code, json_data, cookies=None, headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.cookies = cookies or {}
        self.headers = headers or {
            'x-frame-options': 'SAMEORIGIN',
            'x-content-type-options': 'nosniff',
            'content-type': 'application/json'
        }
        self.text = json.dumps(json_data) if json_data else ""

    def json(self):
        return self._json_data

class TestGlobalEntrySlotChecker(unittest.TestCase):
    def setUp(self):
        self.location_ids = ['14321']
        self.date_start = '2025-02-14'
        self.date_end = '2026-02-14'
        self.checker = GlobalEntrySlotChecker(
            location_ids=self.location_ids,
            date_start=self.date_start,
            date_end=self.date_end
        )

    @patch('requests.Session')
    def test_successful_slot_check(self, mock_session):
        # Setup mock session
        session_instance = mock_session.return_value
        self.checker.session = session_instance  # Replace the session with our mock

        # Mock responses
        refresh_response = MockResponse(
            status_code=200,
            json_data=None,
            cookies={'TS01ddc3cd': 'test-cookie'},
            headers={
                'x-frame-options': 'SAMEORIGIN',
                'set-cookie': 'TS01ddc3cd=test-cookie'
            }
        )
        slots_response = MockResponse(
            status_code=200,
            json_data=[{
                'locationId': '14321',
                'startTimestamp': '2025-02-14T10:00',
                'endTimestamp': '2025-02-14T10:15',
                'duration': 15
            }],
            cookies={'TS01ddc3cd': 'test-cookie'}
        )

        # Set up sequence of responses for session.get
        session_instance.get.side_effect = [refresh_response, slots_response]

        # Test slot checking
        slots = self.checker.check_slots()

        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]['location'], '14321')
        self.assertEqual(slots[0]['date'], '2025-02-14')
        self.assertEqual(slots[0]['time'], '10:00')

        # Verify the correct API calls were made
        self.assertEqual(session_instance.get.call_count, 2)

    @patch('requests.Session')
    def test_no_appointments_available(self, mock_session):
        # Setup mock session
        session_instance = mock_session.return_value
        self.checker.session = session_instance

        # Mock responses for both calls
        refresh_response = MockResponse(200, None, {'session_cookie': 'test-cookie'})
        slots_response = MockResponse(200, [])

        session_instance.get.side_effect = [refresh_response, slots_response]

        slots = self.checker.check_slots()
        self.assertEqual(len(slots), 0)

    @patch('requests.Session')
    def test_http_error_handling(self, mock_session):
        # Setup mock session
        session_instance = mock_session.return_value
        self.checker.session = session_instance

        # Mock responses
        refresh_response = MockResponse(200, None, {'session_cookie': 'test-cookie'})
        error_response = MockResponse(403, None)
        retry_response = MockResponse(200, [])

        session_instance.get.side_effect = [
            refresh_response,  # First refresh
            error_response,    # First attempt fails
            refresh_response,  # Second refresh after error
            retry_response    # Retry succeeds but returns no slots
        ]

        slots = self.checker.check_slots()
        self.assertEqual(len(slots), 0)

    def test_appointment_class(self):
        # Test Appointment class functionality
        appointment = Appointment(
            location_id='14321',
            start_timestamp='2025-02-14T10:00',
            end_timestamp='2025-02-14T10:15',
            duration=15
        )

        self.assertEqual(appointment.date, '2025-02-14')
        self.assertEqual(appointment.time, '10:00')
        self.assertEqual(appointment.duration, 15)

if __name__ == '__main__':
    unittest.main()