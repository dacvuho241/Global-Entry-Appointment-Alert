import requests
import logging

class Notifier:
    def __init__(self, ntfy_topic='vu_alert'):
        self.ntfy_topic = ntfy_topic
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Notifier initialized with ntfy topic: {ntfy_topic}")

    def send_notification(self, message, title='Global Entry Alert'):
        """Send notification through ntfy.sh with custom title"""
        try:
            self.logger.info(f"Attempting to send notification to ntfy.sh/{self.ntfy_topic}")
            url = f"https://ntfy.sh/{self.ntfy_topic}"
            headers = {
                'Title': title,
                'Priority': 'urgent',
                'Tags': 'calendar'
            }
            self.logger.debug(f"Sending message: {message}")
            response = requests.post(url, data=message, headers=headers)
            self.logger.info(f"Notification response status: {response.status_code}")

            if response.status_code == 200:
                self.logger.info("Notification sent successfully")
                return True
            else:
                self.logger.warning(f"Unexpected status code: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending ntfy notification: {str(e)}")
            return False