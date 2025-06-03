import logging

def get_logger(name: str = __name__) -> logging.Logger:
    """
    Get a logger with a level of info including the timestamp, the level of the message and the message itself
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    return logging.getLogger(name)
