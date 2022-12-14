#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import gzip
import json
import logging
import os
import re
import sys
import typing
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
LOG_REGEX = re.compile(r'.+\[.+\] "\w+ (?P<url>/?.*) HTTP.+" \d{3} \d+ .+" (?P<time>[\d.]+)', re.IGNORECASE)
LOG_FORMAT = '[%(asctime)s] %(levelname).1s %(message)s'
LOG_DATE_FORMAT = '%Y.%m.%d%H:%M:%S'
LOG_FILE_DATE_FORMAT = '%Y%m%d'  # формат даты в наименовании файла обрабатываемого лога
REPORT_FILE_DATE_FORMAT = '%Y.%m.%d'  # формат даты для имени файла отчета
REPORT_FILE_NAME_TEMPLATE = 'report-%s.html'
NGINX_LOG_FILE_RE = re.compile(r'nginx-access-ui\.log-([\d]{8})(\.gz|\b)')
ENCODING = 'UTF-8'


def get_config(config=None) -> dict:
    """Возвращает данные конфигурации скрипта"""
    # конфигурация по дефолту
    if config is None:
        config = DEFAULT_CONFIG
    # аргументы командной строки в dict
    parser = argparse.ArgumentParser(prog='log_analizer.py')
    parser.add_argument("--config", dest='config', default=None, help="Файл конфигурации json")
    args = parser.parse_args()

    if args.config:
        # читаем, парсим конфиг файл и обновляем конфиг данными из файла
        try:
            with open(args.config, encoding=ENCODING) as fp:
                config.update(json.load(fp))
        except (FileNotFoundError, FileExistsError) as e:
            raise SystemError(e)
    #
    if 'ERRORS_THRESHOLD' in config:
        et = config.get('ERRORS_THRESHOLD')
        if isinstance(et, str) and et.endswith('%'):
            et = float(et[:-1]) / 100
        else:
            et = float(et)
        config['ERRORS_THRESHOLD'] = et

    return config


def get_last_log_data(config: dict) -> namedtuple:
    """"""
    log_dir = config.get('LOG_DIR')
    log_name, log_date, log_ext = None, None, None

    for fn in os.listdir(log_dir):
        if NGINX_LOG_FILE_RE.fullmatch(fn):
            fd, fe = NGINX_LOG_FILE_RE.findall(fn)[0]
            if log_date is None or fd > log_date:
                log_name, log_date, log_ext = fn, fd, fe  # фиксируем лог с крайней датой

    if not log_name:
        raise SystemExit(f'Не найден файл лога в {log_dir}')

    fdate = datetime.strptime(log_date, LOG_FILE_DATE_FORMAT)  # convert to datetime
    log_data = namedtuple('log_data', 'log_name log_date log_ext')(log_name, fdate, log_ext)

    return log_data


def get_report_name(log_data: namedtuple):
    return REPORT_FILE_NAME_TEMPLATE % log_data.log_date.strftime(REPORT_FILE_DATE_FORMAT)


def report_exists(config, log_data) -> bool:
    """Проверка на наличие отчета на определенную логом дату"""
    report_name = get_report_name(log_data)
    return report_name in os.listdir(config['REPORT_DIR'])


def get_median(data: list) -> typing.Union[int, float]:
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


def parse_log(config: dict, logger: logging.Logger, log_data: namedtuple) -> tuple[dict, int, int]:
    """Парсит лог nginx из файла, указанного в config"""
    log_name = PurePath(config.get('LOG_DIR')) / log_data.log_name
    requests_count = 0  # общее кол-во запросов
    requests_time = 0  # суммарное время всех запросов
    parsing_error_count = 0  # счетчик ошибок парсинга
    parsed_data = {}
    reader = open if not log_data.log_ext else gzip.open

    # парсинг лога по regex
    logger.info(f'Разбор файла {log_name}')
    with reader(log_name, 'rb') as fp:
        for row in fp:
            line = row.decode(encoding=ENCODING)
            matched = LOG_REGEX.match(line)
            if matched:
                row_data = matched.groupdict()
                data = parsed_data.setdefault(row_data['url'], [])
                url_request_time = float(row_data['time'])
                requests_time += url_request_time
                data.append(url_request_time)
                logger.debug(row_data)
            else:
                # считаем ошибка парсинга
                logger.error(f'Ошибка разбора: {line}')
                parsing_error_count += 1

            requests_count += 1

    # проверка количества записей
    if requests_count == 0 and parsing_error_count == 0:
        raise SystemError(
            f'Ошибка парсинга или пустой лог-файл {log_name}, найдено строк: {requests_count}, ошибок: {parsing_error_count}')

    logger.info(f'Обработано строк: {requests_count}')

    # проверка разбора на ошибки
    if parsing_error_count > 0:
        logger.info(f'Ошибок при разборе: {parsing_error_count}')
    err_perc = parsing_error_count / requests_count  # % ошибок
    error_threshold = config.get('ERRORS_THRESHOLD', None)
    if error_threshold and err_perc > error_threshold:
        raise SystemError(f'Превышен порог допустимого количества ошибок при разборе в {error_threshold * 100}%!')

    return parsed_data, requests_count, requests_time


def calculate_stat(config, logger, parsed_map, requests_count, requests_time) -> dict:
    """Расчет статистики по url'ам"""
    logger.info('Расчет статистики по url')
    for url, data in parsed_map.items():
        stat_map = {}
        _count = len(data)  # количество фиксаций
        stat_map['count'] = _count
        stat_map['count_perc'] = round(_count / requests_count * 100, 3)  # процент от общего количества
        _time_sum = round(sum(data), 3)  # суммарное время для url
        stat_map['time_sum'] = _time_sum
        stat_map['time_perc'] = round(_time_sum / requests_time * 100, 3)  # суммарное время для url в процентах
        stat_map['time_avg'] = round(_time_sum / _count, 3)  # среднее время
        stat_map['time_max'] = max(data)  # максимальное время
        stat_map['time_med'] = get_median(data)  # медиана
        #
        logger.debug(f'calc stat {url} - in:{data} :: out:{stat_map}')
        parsed_map[url] = stat_map

    return parsed_map


def gen_report_data(config, logger, parsed_map) -> dict:
    """Подготовка данных по url'ам для генерации отчета"""
    # выдача отсортированных данных по time_sum в количестве REPORT_SIZE
    given = 0
    data_list = sorted(parsed_map.items(), key=lambda t: t[1]['time_sum'])
    # data_list = result.items()
    for url, data in reversed(data_list):  # сортировка по-убыванию
        # for url, data in data_list:  # сортировка по-возрастанию
        if given >= config['REPORT_SIZE']:
            break

        yield {'url': url, **data}

        given += 1
    logger.info(f'Сгенерировано строк данных в отчет: {given}')


def generate_report(config: dict, logger: logging.Logger, parsed_log: dict, log_data: namedtuple):
    """"""
    report_name = get_report_name(log_data)

    with open(os.path.join(os.path.dirname(__file__), 'report.html'), encoding=ENCODING) as fp:
        templ = Template(fp.read())

    # запуск процесса формирования данных для отчета и сериализуем в json
    table = json.dumps([m for m in parsed_log], indent=2)
    templ.safe_substitute(table_json=table)

    report_path = os.path.join(config['REPORT_DIR'], report_name)
    with open(report_path, 'w', encoding=ENCODING) as fp:
        fp.write(templ.safe_substitute(table_json=table))

    logger.info(f'Сформирован отчет {report_path}')


def main():
    try:
        config = get_config()
        # set logger
        loglevel = config.get('LOGLEVEL', 'INFO')
        logfile = config.get('LOGFILE', None)
        logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, filename=logfile, level=loglevel)
        logger = logging.getLogger(__name__)

        log_data = get_last_log_data(config)  # поиск последнего лога

        if report_exists(config, log_data):  # выходим, если отчет на определенную дату уже существует
            raise SystemExit(f"Отчет уже создан: {os.path.join(config['REPORT_DIR'], get_report_name(log_data))}")

        parsed_log_data = parse_log(config, logger, log_data)  # разбор данных лога и подготовка данных для отчета
        stat = calculate_stat(config, logger, *parsed_log_data)  # подсчет статистики
        report_data = gen_report_data(config, logger, stat)  # генератор данных для отчета
        generate_report(config, logger, report_data, log_data)  # формирование отчета

    except SystemError as e:
        logger.error(e)
        sys.exit(1)

    except SystemExit as e:
        logger.info(e)

    except Exception as e:
        logging.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()
