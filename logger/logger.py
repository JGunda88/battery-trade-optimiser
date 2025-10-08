import inspect
import logging
import uuid

from logging.handlers import RotatingFileHandler
from logger.settings import LOGGING_DEBUG_LEVEL, LOGGING_FILENAME, LOGGING_BACKUP_COUNT, LOGGING_MAX_BYTES


def set_logging(debug_level=LOGGING_DEBUG_LEVEL, log_filename=LOGGING_FILENAME, announce_initialisation=False):
    """
    Sets the format of logging, output filename and debug level

    :param debug_level: possible values are DEBUG, INFO, WARNING, ERROR, CRITICAL. If debug_level is of an unknown
                        type, then 'DEBUG' will be used
    :type debug_level:string
    :param log_filename: the name of the log file to be used by logging
    :type log_filename: string
    :param announce_initialisation: if set to TRUE, a configuration message will be output into log_filename
    :type announce_initialisation: Boolean
    :return logger
    """

    logger = logging.getLogger('orchestrator')
    if not debug_level.lower() in {'debug', 'info', 'warning', 'error', 'critical'}:
        debug_level = 'debug'

    logging.basicConfig(
        filename=log_filename,
        format="%(asctime)s-%(name)s - [%(levelname)s] %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S %p",
        level=logging.__dict__[debug_level.upper()]
    )
    logger.addHandler(RotatingFileHandler(log_filename, maxBytes=LOGGING_MAX_BYTES, backupCount=LOGGING_BACKUP_COUNT))
    if announce_initialisation:
        msg = 'logging is set up now - using logging level {}'.format(logging.__dict__[debug_level.upper()])
        logger.debug(msg)
    return logger


logger = set_logging()


def log_this(logger=logger, input_args_dump=False):
    def log_this_decorator(func):
        def func_wrapper(*args, **kwargs):
            r = inspect.stack()
            parents_name = r[1][1]
            unique_uuid = uuid.uuid4().hex.upper()

            # log START of CALL
            logger.info("{}:{} #{} CALL".format(parents_name, func.__name__, unique_uuid))

            if input_args_dump:
                # log both positional and optional argument names and argument values
                args_name = inspect.getargspec(func)[0]
                args_dict = dict(zip(args_name, args))
                for arg in args_dict:
                    logger.debug("input (positional) argument {}={}".format(arg, args_dict[arg]))
                for arg in kwargs:
                    logger.debug("input (optional) argument {}={}".format(arg, kwargs[arg]))

            # proceed with executing the function
            res = func(*args, **kwargs)

            # log END of CALL
            logger.info("{}:{} #{} END of CALL".format(parents_name, func.__name__, unique_uuid))
            return res

        func_wrapper.__name__ = func.__name__
        func_wrapper.__doc__ = func.__doc__
        return func_wrapper()

    return log_this_decorator()
