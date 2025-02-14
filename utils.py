import logging

def setup_logging():
    """Configure logging settings"""
    logging.basicConfig(
        level=logging.DEBUG,  # Changed from INFO to DEBUG for more detailed logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Reduce noise from external libraries while keeping our debug logs
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)