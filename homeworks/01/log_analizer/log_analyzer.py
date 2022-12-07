#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import collections
import gzip
import json
import logging
import os
import re
import sys
import typing
from pathlib import PurePath

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
NGINX_LOG_FILE_RE = re.compile(r'nginx-access-ui\.log-([\d]+)(\.gz|\b)')
ENCODING = 'UTF-8'


def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(prog='log_analizer.py')
    parser.add_argument("--config", dest='config', default=None, help="Файл конфигурации json")

    return parser.parse_args()


def get_config() -> dict:
    """Возвращает данные конфигурации скрипта"""
    # конфигурация по дефолту
    config = DEFAULT_CONFIG

    # аргументы командной строки в dict
    args = parse_args()
    # config_file = args.config

    if args.config:
        # читаем, парсим конфиг файл и обновляем конфиг данными из файла
        with open(args.config) as fp:
            config.update(json.load(fp))

    # обновляем конфиг данными командной строки
    # config.update(args)
    return config


def get_logger(config):
    """Logger"""
    loglevel = config.get('LOGLEVEL', 'INFO')
    logfile = config.get('LOGFILE', None)
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, filename=logfile, level=loglevel)
    logger = logging.getLogger(__name__)
    return logger


def get_last_log(config) -> tuple:
    """"""
    logdir = config.get('LOG_DIR')
    fname, fdate, fext = None, None, None

    for fn in os.listdir(logdir):
        if NGINX_LOG_FILE_RE.fullmatch(fn):
            fd, fe = NGINX_LOG_FILE_RE.findall(fn)[0]
            if fdate is None or fd > fdate:
                fname, fdate, fext = fn, fd, fe  # фиксируем лог с крайней датой

    return fname, fdate, fext[1:] if fext else fext  #


def parse_log(config, logger, last_log) -> typing.Generator:
    """Парсит лог nginx из файла, указанного в config. Возвращает генератор"""
    log_name, log_date, log_ext = last_log
    if not log_name:
        raise SystemExit('Не найден лог-файл')

    reader = open if not log_ext else gzip.open
    log_name = PurePath(config.get('LOG_DIR')) / log_name

    regex = re.compile(r'.*"(GET|POST|PUT|DELETE) (.*) HTTP.*" .* ([\d.]+)')
    # regex = re.compile(r'([\d.]+) ([\s]+).*\[.*\] "(GET|POST) (.*) HTTP/.*" ([\d+]) ([\d+]) "" "" "" "" "" ([\d.]+)')
    requests_count = 0  # общее кол-во запросов
    counter = collections.Counter()
    with reader(log_name, 'r', encoding=ENCODING) as fp:
        a = 1000
        for row in fp:
            a -= 1
            if not a:
                break
            data = regex.findall(row)
            print(row, data)
            if not len(data):
                continue
            method, url, req_time = data[0]
            # print(url, req_time)
            requests_count += 1
            counter[url] += 1
    return
    # yield 1


def generate_report(config, logger, parsed_log):
    """"""


def main():
    try:
        config = get_config()
        logger = get_logger(config)
        last_log = get_last_log(config)
        parsed_log = parse_log(config, logger, last_log)
        generate_report(config, logger, parsed_log)

    except SystemError as e:
        logger.error(e)

    except SystemExit as e:
        logger.info(e)

    except Exception as e:
        logging.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
