import logging
__version__ = "0.0.1"
__log_format__ = "%(asctime)s.%(msecs)%02d %(levelname)-8s %(name)-15s [%(filename)s:%(lineno)d] %(message)s"
__log_date_format__ = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(format=__log_format__, datefmt=__log_date_format__)