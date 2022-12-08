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
from datetime import datetime
from pathlib import PurePath

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

DEFAULT_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    # 'ERRORS_THRESHOLD': None,
    }

LOG_FORMAT = '[%(asctime)s] %(levelname).1s %(message)s'
LOG_DATE_FORMAT = '%Y.%m.%d%H:%M:%S'
LOG_FILE_DATE_FORMAT = '%Y%m%d'  # формат даты в наименовании файла обрабатываемого лога
REPORT_FILE_DATE_FORMAT = '%Y.%m.%d'  # формат даты для имени файла отчета
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

    if args.config:
        # читаем, парсим конфиг файл и обновляем конфиг данными из файла
        with open(args.config) as fp:
            config.update(json.load(fp))

    #
    if 'ERROR_THRESHOLD' in config:
        et = config.get('ERROR_THRESHOLD')
        if et.endswith('%'):
            et = int(et[:-1]) / 100
        else:
            et = float(et)
        config['ERROR_THRESHOLD'] = et

    return config


def get_logger(config):
    """Logger"""
    loglevel = config.get('LOGLEVEL', 'INFO')
    logfile = config.get('LOGFILE', None)
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, filename=logfile, level=loglevel)
    logger = logging.getLogger(__name__)
    return logger


def get_last_log_data(config, logger) -> tuple:
    """"""
    logdir = config.get('LOG_DIR')
    fname, fdate, fext = None, None, None

    for fn in os.listdir(logdir):
        if NGINX_LOG_FILE_RE.fullmatch(fn):
            fd, fe = NGINX_LOG_FILE_RE.findall(fn)[0]
            if fdate is None or fd > fdate:
                fname, fdate, fext = fn, fd, fe  # фиксируем лог с крайней датой

    fdate = datetime.strptime(fdate, LOG_FILE_DATE_FORMAT)  # convert to datetime

    return fname, fdate, fext[1:] if fext else fext


def get_mediana(data: list):
    """Расчет медианы выборки"""
    data = sorted(data)
    lcnt = len(data)
    half = lcnt // 2
    if lcnt == 0:
        return 0
    if lcnt % 2 > 0:  #
        return data[half]
    else:
        return round(sum(data[half - 1: half + 1]) / 2, 3)


def parse_log(config, logger, log_name, log_ext) -> tuple:
    """Парсит лог nginx из файла, указанного в config. Возвращает генератор"""
    if not log_name:
        raise SystemExit('Не найден файл')

    regex = re.compile(r'.+"(?P<method>GE|POST) (?P<url>.+) HTTP.+ (?P<code>\d{3}) (?P<size>\d+) .+" (?P<time>[\d.]+)',
                       re.IGNORECASE)
    log_name = PurePath(config.get('LOG_DIR')) / log_name
    requests_count = 0  # общее кол-во запросов
    requests_time = 0  # суммарное время всех запросов
    parsing_error_count = 0  # счетчик ошибок парсинга
    result = {}
    reader = open if not log_ext else gzip.open

    with reader(log_name, 'r', encoding=ENCODING) as fp:
        n = 1000
        for row in fp:
            if n == 0:
                break
            n -= 1

            matched = regex.match(row)
            if matched:
                parsed_data = matched.groupdict()
                data = result.setdefault(parsed_data['url'], [])
                url_request_time = float(parsed_data['time'])
                requests_time += url_request_time
                data.append(url_request_time)
            else:
                # считаем ошибка парсинга
                logger.error(f'Ошибка разбора: {row}')
                parsing_error_count += 1

            requests_count += 1

    # проверка количества записей
    if requests_count == 0 and parsing_error_count == 0:
        raise SystemError(f'Лог-файл {log_name} найдено строк: {requests_count}')

    logger.info(f'Обработано строк: {requests_count}')

    # проверка разбора на ошибки
    if parsing_error_count > 0:
        logger.info(f'Ошибок разбора: {parsing_error_count}')
    err_perc = parsing_error_count / requests_count  # % ошибок
    error_threshold = config.get('ERROR_THRESHOLD', None)
    if error_threshold and err_perc > error_threshold:
        raise SystemError(f'Превышен порог допустимого количества ошибок при разборе в {error_threshold * 100}%!')

    # расчет статистики по url
    for url, data in result.items():
        count = len(data)  # количество фиксаций
        count_perc = round(count / requests_count * 100, 2)  # процент от общего количества
        time_sum = round(sum(data), 3)  # суммарное время для url
        time_perc = round(time_sum / requests_time * 100, 2)  # суммарное время для url в процентах
        time_avg = round(time_sum / count, 3)  # среднее время
        time_max = max(data)  # максимальное время
        time_med = get_mediana(data)  # медиана
        #
        stat_data = [count, count_perc, time_sum, time_perc, time_avg, time_max, time_med]
        logger.debug(f'calc stat {url} - in:{data} :: out:{stat_data}')
        result[url] = stat_data

    # выдача данных
    for url, data in result.items():
        if data[6] > 10:
            yield url, data


def generate_report(config, logger, fdate, parsed_log):
    """"""
    for url, data in parsed_log:
        print(url, data)


def main():
    try:
        config = get_config()
        logger = get_logger(config)
        fname, fdate, fext = get_last_log_data(config, logger)
        parsed_data = parse_log(config, logger, fname, fext)
        generate_report(config, logger, fdate, parsed_data)

    except SystemError as e:
        logger.error(e)

    except SystemExit as e:
        logger.info(e)

    except Exception as e:
        logging.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
