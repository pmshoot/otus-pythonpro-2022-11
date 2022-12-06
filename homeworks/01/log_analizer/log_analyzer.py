#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import typing

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

DEFAULT_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}
LOG_FORMAT = '[%(asctime)s] %(levelname).1s %(message)s'
LOG_DATE_FORMAT = '%Y.%m.%d%H:%M:%S'


def get_config():
    """"""

    # parse: --config, --logfile, --loglevel, --err-threshold
    raise FileNotFoundError('No config!')


def get_logger(config):
    """"""
    loglevel = config.get('loglevel', 'INFO')
    logfile = config.get('logfile', None)
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, filename=logfile, level=loglevel)
    logger = logging.getLogger(__name__)
    return logger


def parse_log_gen(config, logger) -> typing.Generator:
    """Парсит лог nginx из файла, указанного в config. Возвращает генератор"""


def generate_report(config, logger, parsed_log):
    """"""


def main():
    try:
        config = get_config()
        logger = get_logger(config)
        parsed_log = parse_log_gen(config, logger)
        generate_report(config, logger, parsed_log)

    except Exception as e:
        logging.exception(e)


if __name__ == "__main__":
    main()
