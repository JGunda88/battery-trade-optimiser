"""
Constant settings related to logging mechanism
"""
import os

LOGGING_DEBUG_LEVEL = 'INFO'  # possible options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGGING_FILENAME = os.getenv('LOGGING_FILENAME', default='log.txt')
LOGGING_BACKUP_COUNT = 5
LOGGING_MAX_BYTES = 20*1024*1024
