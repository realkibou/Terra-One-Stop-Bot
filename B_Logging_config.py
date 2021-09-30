#!/usr/bin/python3

import B_Config as config

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
            'level': 'DEBUG',
            'handlers': ['default'],
            'propagate': False
        },
        'report_logger': {
            'level': 'INFO',
            # As .info does not exists for default. This makes sure that also warnings are included in the report.
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
            'format': '%(asctime)s [%(levelname)s] |%(lineno)s: %(message)s',
            'datefmt': '%d-%m-%Y %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(process)d: %(module)s|%(lineno)s: %(message)s',
            'datefmt': '%d-%m-%Y %H:%M:%S'
        },
    },
}
