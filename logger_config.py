import logging
import os

def setup_logger():
    """
    Configures a centralized logger that writes to both the console
    and a rotating text file in the project directory.
    """
    # Create a logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Create root logger
    logger = logging.getLogger("TcgSorter")
    logger.setLevel(logging.DEBUG)  # Capture everything from DEBUG up to CRITICAL

    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # 1. Console Handler (Cleaner output for the developer)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Hide noisy DEBUG logs in console
    console_format = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(console_format)

    # 2. File Handler (Deep diagnostics, includes strict DEBUG timestamps)
    file_handler = logging.FileHandler('logs/sorter.log', mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Log everything to the file
    file_format = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_format)

    # Add handlers to the root logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info("📝 Centralized logger initialized. Writing detailed logs to 'logs/sorter.log'")
    return logger
