#!/usr/bin/python3

# Other assets
import B_Config as config

# Other imports
import os
import logging.config
import io

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
        if not os.path.exists('./logs'):
            os.makedirs('logs')

        logging.config.dictConfig(LOGGING_CONFIG)
        self.default_logger = logging.getLogger('default_logger')
        self.report_logger = logging.getLogger('report_logger')

        self.report_array = io.StringIO()
        self.report_handler = logging.StreamHandler(self.report_array)
        self.report_logger.addHandler(self.report_handler)
        self.default_logger.addHandler(self.report_handler)