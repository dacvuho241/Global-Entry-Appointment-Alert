import os
import time
import logging
from config import load_config
from slot_checker import GlobalEntrySlotChecker
from notifier import Notifier
from utils import setup_logging

def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = load_config()

        # Initialize components
        slot_checker = GlobalEntrySlotChecker(
            location_ids=config['LOCATION_IDS'],
            date_start=config['DATE_START'],
            date_end=config['DATE_END']
        )

        notifier = Notifier(ntfy_topic=config['NTFY_TOPIC'])

        logger.info("Global Entry Slot Notifier started")

        # Send a test notification on startup
        logger.info("Sending test notification...")
        test_slots = slot_checker.get_test_slot()
        for slot in test_slots:
            message = (
                f"🧪 Test Notification\n"
                f"Location: {slot['location']}\n"
                f"Date: {slot['date']}\n"
                f"Time: {slot['time']}"
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
                        message = (
                            f"🎉 Global Entry Appointment Available!\n"
                            f"Location: {slot['location']}\n"
                            f"Date: {slot['date']}\n"
                            f"Time: {slot['time']}"
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