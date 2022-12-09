#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import gzip
import json
import logging
import os
import re
import sys
from collections import namedtuple
from datetime import datetime
from pathlib import PurePath
from string import Template

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

# const
# LOG_REGEX = r'.+"(?P<method>GET|POST) (?P<url>.+) HTTP.+ (?P<code>\d{3}) (?P<size>\d+) .+" (?P<time>[\d.]+)'
LOG_REGEX = r'.+ ("(?P<method>[\w]+) (?P<url>.+) HTTP.+"|"0") (?P<code>\d{3}) (?P<size>\d+) .+" (?P<time>[\d.]+)'
LOG_FORMAT = '[%(asctime)s] %(levelname).1s %(message)s'
LOG_DATE_FORMAT = '%Y.%m.%d%H:%M:%S'
LOG_FILE_DATE_FORMAT = '%Y%m%d'  # формат даты в наименовании файла обрабатываемого лога
REPORT_FILE_DATE_FORMAT = '%Y.%m.%d'  # формат даты для имени файла отчета
REPORT_FILE_NAME_TEMPLATE = 'report-%s.html'
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
    log_name, log_date, log_ext = None, None, None

    for fn in os.listdir(logdir):
        if NGINX_LOG_FILE_RE.fullmatch(fn):
            fd, fe = NGINX_LOG_FILE_RE.findall(fn)[0]
            if log_date is None or fd > log_date:
                log_name, log_date, log_ext = fn, fd, fe  # фиксируем лог с крайней датой

    if not log_name:
        raise SystemExit('Не найден файл лога')
    logger.info(f'Найден файл {log_name}')

    fdate = datetime.strptime(log_date, LOG_FILE_DATE_FORMAT)  # convert to datetime
    log_data = namedtuple('log_data', 'log_name log_date log_ext')(log_name, fdate, log_ext)

    return log_data


def get_report_name(log_date: datetime) -> str:
    """"""
    return REPORT_FILE_NAME_TEMPLATE % log_date.strftime(REPORT_FILE_DATE_FORMAT)


def report_exists(config: dict, report_name: str) -> bool:
    """"""
    return report_name in os.listdir(config['REPORT_DIR'])


def get_median(data: list):
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


def gen_parse_log(config, logger, log_data):
    """Парсит лог nginx из файла, указанного в config. Возвращает генератор"""
    regex = re.compile(LOG_REGEX, re.IGNORECASE)
    log_name = PurePath(config.get('LOG_DIR')) / log_data.log_name
    requests_count = 0  # общее кол-во запросов
    requests_time = 0  # суммарное время всех запросов
    parsing_error_count = 0  # счетчик ошибок парсинга
    result = {}
    reader = open if not log_data.log_ext else gzip.open

    with reader(log_name, 'rb') as fp:
        for row in fp:
            line = row.decode(encoding=ENCODING)
            matched = regex.match(line)
            if matched:
                parsed_data = matched.groupdict()
                data = result.setdefault(parsed_data['url'], [])
                url_request_time = float(parsed_data['time'])
                requests_time += url_request_time
                data.append(url_request_time)
                logger.debug(parsed_data)
            else:
                # считаем ошибка парсинга
                logger.error(f'Ошибка разбора: {line}')
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
        stat_map = {}
        _count = len(data)  # количество фиксаций
        stat_map['count'] = _count
        stat_map['count_perc'] = _count / requests_count * 100  # процент от общего количества
        _time_sum = sum(data)  # суммарное время для url
        stat_map['time_sum'] = _time_sum
        stat_map['time_perc'] = _time_sum / requests_time * 100  # суммарное время для url в процентах
        stat_map['time_avg'] = _time_sum / _count  # среднее время
        stat_map['time_max'] = max(data)  # максимальное время
        stat_map['time_med'] = get_median(data)  # медиана
        #
        logger.debug(f'calc stat {url} - in:{data} :: out:{stat_map}')
        result[url] = stat_map

    # выдача данных
    pushed = 0
    data_list = sorted(result.items(), key=lambda t: t[1]['time_sum'])
    for url, data in data_list:
        if pushed > config['REPORT_SIZE']:
            raise StopIteration
        yield {'url': url, **stat_map}


def generate_report(config: dict, logger: logging.Logger, parsed_log, log_data):
    """"""
    report_name = get_report_name(log_data.log_date)
    if report_exists(config, report_name):
        raise SystemExit(f"Отчет уже создан: {os.path.join(config['REPORT_DIR'], report_name)}")

    with open('report.html', encoding=ENCODING) as fp:
        templ = Template(fp.read())

    table = json.dumps([m for m in parsed_log])
    templ.safe_substitute(table_json=table)

    report_path = os.path.join(config['REPORT_DIR'], report_name)
    with open(report_path, 'w', encoding=ENCODING) as fp:
        fp.write(templ.safe_substitute(table_json=table))

    logger.info(f'Создан отчет {report_path}')


def main():
    try:
        config = get_config()
        logger = get_logger(config)
        log_data = get_last_log_data(config, logger)
        parsed_log = gen_parse_log(config, logger, log_data)
        generate_report(config, logger, parsed_log, log_data)

    except SystemError as e:
        logger.error(e)

    except SystemExit as e:
        logger.info(e)

    except Exception as e:
        logging.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
