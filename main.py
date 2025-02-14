import os
import time
import logging
import argparse
from config import load_config
from slot_checker import GlobalEntrySlotChecker
from notifier import Notifier
from utils import setup_logging

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Global Entry Appointment Slot Checker')
    parser.add_argument('-l', '--location', required=True,
                        help='Location ID to check for appointments')
    parser.add_argument('-n', '--notifier', required=True,
                        choices=['ntfy'],
                        help='Notification service to use (currently only ntfy supported)')
    parser.add_argument('-t', '--topic', default='vu_alert',
                        help='ntfy.sh topic for notifications (default: vu_alert)')
    parser.add_argument('-i', '--interval', type=int, default=300,
                        help='Time between checks in seconds (default: 300)')
    return parser.parse_args()

def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Parse command line arguments
        args = parse_args()

        # Update config with command line arguments
        config = {
            'LOCATION_IDS': [args.location],
            'DATE_START': load_config()['DATE_START'],
            'DATE_END': load_config()['DATE_END'],
            'CHECK_INTERVAL': args.interval,
            'NTFY_TOPIC': args.topic
        }

        # Initialize components
        slot_checker = GlobalEntrySlotChecker(
            location_ids=config['LOCATION_IDS'],
            date_start=config['DATE_START'],
            date_end=config['DATE_END']
        )

        notifier = Notifier(ntfy_topic=config['NTFY_TOPIC'])

        logger.info("Global Entry Slot Notifier started")
        logger.info(f"Checking location ID: {args.location}")
        logger.info(f"Using notifier: {args.notifier}")
        logger.info(f"Check interval: {args.interval} seconds")

        # Send a test notification on startup
        logger.info("Sending test notification...")
        test_slots = slot_checker.get_test_slot()
        for slot in test_slots:
            message = (
                f"🧪 Test Alert: {slot['location_name']} Monitor Started\n"
                f"Location: {slot['location_name']}\n"
                f"Current Time: {slot['time']}\n"
                f"Monitoring for available appointments..."
            )
            success = notifier.send_notification(message)
            logger.info(f"Test notification {'sent successfully' if success else 'failed'}")

        while True:
            try:
                # Check for available slots
                available_slots = slot_checker.check_slots()

                if available_slots:
                    # Send notifications for available slots
                    for slot in available_slots:
                        times_str = '\n'.join([f"- {time}" for time in slot['times']])
                        message = (
                            f"🎉 Global Entry Appointments Available!\n"
                            f"Location: {slot['location_name']}\n"
                            f"Date: {slot['date']}\n"
                            f"Available times:\n{times_str}"
                        )
                        notifier.send_notification(message)

                # Wait before next check
                time.sleep(config['CHECK_INTERVAL'])

            except Exception as e:
                logger.error(f"Error during slot check: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying

    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
        raise

if __name__ == "__main__":
    main()