#!/usr/bin/python3

# Other assets
import B_Config as config

# Other imports
from os import makedirs, path
from io import StringIO
from logging import getLogger, StreamHandler
from logging.config import dictConfig

if config.Debug_mode:
    level = 'DEBUG'
else:
    level = 'WARNING'

# Logging setup
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'loggers': {
        'default_logger': {
            'level': level,
            'handlers': ['default', 'report'],
            'propagate': False
        },
        'report_logger': {
            'level': 'INFO',
            'handlers': ['default', 'report'],
            'propagate': False
        },
    },
    'handlers': {
        'default': {
            'level': "DEBUG",
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/default.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 3,
            'formatter': 'moderate'  # Set to detailed if you fancy so.
        },
        'report': {
            'level': "INFO",
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/report.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 3,
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(message)s',
            'datefmt': '%d-%m-%Y %H:%M:%S'
        },
        'moderate': {
            'format': '%(asctime)s [%(levelname)s] %(module)s|%(lineno)s: %(message)s',
            'datefmt': '%d-%m-%Y %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(process)d: %(module)s|%(lineno)s: %(message)s',
            'datefmt': '%d-%m-%Y %H:%M:%S'
        },
    },
}

class Logger:
    if config.Debug_mode: print(f'Logger Class loaded.')
    def __init__(self):
        if not path.exists('./logs'):
            makedirs('logs')

        dictConfig(LOGGING_CONFIG)
        self.default_logger = getLogger('default_logger')
        self.report_logger = getLogger('report_logger')

        self.report_array = StringIO()
        self.report_handler = StreamHandler(self.report_array)
        self.report_logger.addHandler(self.report_handler)
        self.default_logger.addHandler(self.report_handler)