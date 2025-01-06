
import logging

logging.basicConfig(
    filename='logs.txt',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)

def log_event(message, level='info'):
    if level == 'info':
        logging.info(message)
    elif level == 'error':
        logging.error(message)
    else:
        logging.debug(message)