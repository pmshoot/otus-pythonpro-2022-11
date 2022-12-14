import datetime
import gzip
import json
import logging
import os.path
import re
import sys
import tempfile
import time
import typing
import unittest
from collections import namedtuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loganalizer.loganalizer import DEFAULT_CONFIG, ENCODING, calculate_stat, \
    gen_report_data, \
    generate_report, get_config, \
    get_last_log_data, \
    get_median, parse_log, get_report_name, report_exists

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


class TestLogAnalizer(unittest.TestCase):
    """"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def setUp(self) -> None:
        """"""
        # очистка параметров командной строки, заданные в некоторых тестах
        if len(sys.argv) > 1:
            sys.argv = [sys.argv[0]]

    def tearDown(self) -> None:
        """"""

    def test_parse_log(self):
        """"""
        expected = (
            {
                '/api/1/banners/?campaign=7789704': [1.0, 2.0, 5.0, 3.0, 4.0],
                '/api/v2/slot/4705/groups': [.1, .2, .7, .7, .8, .9],
                '/api/v2/banner/7763463': [.181],
                '/accounts/login/': [.256, .3],
                '/api/v2/internal/storage/gpmd_plan_report/result.csv.gz': [.062, .062, .062],
                '/accounts/login/?next=/': [.107, .017, .007],
                '/': [.007, .007, .007],
                '/api/v2/target/12988/list?status=1': [.003, .005, .003],
            },
            28,
            19.486,
        )
        fixtures = [
            ({'LOG_DIR': 'log'}, False),
            ({'LOG_DIR': 'log_gz'}, False),
            ({'LOG_DIR': 'log', 'ERRORS_THRESHOLD': '5%'}, True),
            ({'LOG_DIR': 'log_gz', 'ERRORS_THRESHOLD': 0.05}, True),
        ]

        for conf, has_error in fixtures:
            config = get_config(conf)
            log_data = get_last_log_data(config)
            if has_error:
                with self.assertRaises(SystemError):
                    parse_log(config, logger, log_data)
            else:
                result = parse_log(config, logger, log_data)
                self.assertIsInstance(result, tuple)

                parsed_data, requests_count, requests_time = result
                self.assertDictEqual(parsed_data, expected[0])
                self.assertEqual(requests_count, expected[1])
                self.assertEqual(round(requests_time, 3), expected[2])

    def test_calculate_stat(self):
        expected = {
            '/api/1/banners/?campaign=7789704': {'count': 5, 'count_perc': 17.857, 'time_sum': 15.0,
                                                 'time_perc': 76.978, 'time_avg': 3.0, 'time_max': 5.0,
                                                 'time_med': 3.0},
            '/api/v2/slot/4705/groups': {'count': 6, 'count_perc': 21.429, 'time_sum': 3.4, 'time_perc': 17.448,
                                         'time_avg': 0.567, 'time_max': 0.9, 'time_med': 0.7},
            '/api/v2/banner/7763463': {'count': 1, 'count_perc': 3.571, 'time_sum': 0.181, 'time_perc': 0.929,
                                       'time_avg': 0.181, 'time_max': 0.181, 'time_med': 0.181},
            '/accounts/login/': {'count': 2, 'count_perc': 7.143, 'time_sum': 0.556, 'time_perc': 2.853,
                                 'time_avg': 0.278, 'time_max': 0.3, 'time_med': 0.278},
            '/api/v2/internal/storage/gpmd_plan_report/result.csv.gz': {'count': 3, 'count_perc': 10.714,
                                                                        'time_sum': 0.186, 'time_perc': 0.955,
                                                                        'time_avg': 0.062, 'time_max': 0.062,
                                                                        'time_med': 0.062},
            '/accounts/login/?next=/': {'count': 3, 'count_perc': 10.714, 'time_sum': 0.131, 'time_perc': 0.672,
                                        'time_avg': 0.044, 'time_max': 0.107, 'time_med': 0.017},
            '/': {'count': 3, 'count_perc': 10.714, 'time_sum': 0.021, 'time_perc': 0.108, 'time_avg': 0.007,
                  'time_max': 0.007, 'time_med': 0.007},
            '/api/v2/target/12988/list?status=1': {'count': 3, 'count_perc': 10.714, 'time_sum': 0.011,
                                                   'time_perc': 0.056, 'time_avg': 0.004, 'time_max': 0.005,
                                                   'time_med': 0.003}}
        config = get_config({'LOG_DIR': 'log'})
        log_data = get_last_log_data(config)
        parsed_data = parse_log(config, logger, log_data)
        stat = calculate_stat(config, logger, *parsed_data)

        self.assertDictEqual(expected, stat)

    def test_gen_report_data(self):
        fixtures = (
            ({'LOG_DIR': 'log', 'REPORT_SIZE': 30}, 8, False),
            ({'LOG_DIR': 'log', 'REPORT_SIZE': 5}, 5, False),
            ({'LOG_DIR': 'log', 'REPORT_SIZE': 1}, 1, False),
        )

        for conf_data, length, err_exp in fixtures:
            with tempfile.NamedTemporaryFile('w', encoding=ENCODING) as tmpdir:
                conf_data['REPORT_DIR'] = tmpdir.name
                config = get_config(conf_data)

                log_data = get_last_log_data(config)
                parsed_data = parse_log(config, logger, log_data)
                stat = calculate_stat(config, logger, *parsed_data)
                result = gen_report_data(config, logger, stat)

                self.assertIsInstance(result, typing.Generator)
                self.assertEqual(length, len(list(result)))

    def test_generate_report(self):
        fixtures = (
            {'LOG_DIR': 'log', 'REPORT_SIZE': 100},
        )
        with tempfile.TemporaryDirectory(prefix='test_') as tmpdir:
            for conf_data in fixtures:
                conf_data['REPORT_DIR'] = tmpdir
                config = get_config(conf_data)

                log_data = get_last_log_data(config)

                # нет отчета
                self.assertFalse(report_exists(config, log_data))

                parsed_data = parse_log(config, logger, log_data)
                stat = calculate_stat(config, logger, *parsed_data)
                result = gen_report_data(config, logger, stat)

                generate_report(config, logger, result, log_data)

                listing = os.listdir(tmpdir)
                self.assertEqual(len(listing), 1)
                report_name = get_report_name(log_data)
                self.assertEqual(report_name, listing[0])

                # уже есть отчет
                self.assertTrue(report_exists(config, log_data))

    def test_log_regex(self):
        regex = re.compile(r'.+\[.+\] "\w+ (?P<url>/?.*) HTTP.+" \d{3} \d+ .+" (?P<time>[\d.]+)', re.IGNORECASE)
        # regex = re.compile(r'.+ ".+ (?P<url>/.*) HTTP.+" \d{3} \d+ .+" (?P<time>[\d.]+)', re.IGNORECASE)
        configs = [
            ({'LOG_DIR': 'log'}, open),
            ({'LOG_DIR': 'log_empty'}, open),
            ({'LOG_DIR': 'log_gz'}, gzip.open),
        ]

        for config, rdr in configs:
            log_data = get_last_log_data(config)
            reader = open if not log_data.log_ext else gzip.open
            self.assertEqual(reader, rdr, 'неверный ридер')

            log_path = os.path.join(config['LOG_DIR'], log_data.log_name)
            with reader(log_path, 'rb') as fp:
                for n, row in enumerate(fp):
                    line = row.decode(encoding=ENCODING)
                    if not line:
                        continue
                    log, must_match = line.split('||')
                    matched = regex.match(log)
                    if matched:
                        self.assertTrue(eval(must_match))
                        self.assertIsNotNone(matched, f'[{n}] {line}, {matched.groupdict()}')
                    else:
                        self.assertFalse(eval(must_match))
                        self.assertIsNone(matched, f'[{n}] {line}')

    def test_get_median(self):
        fixtures = [
            ([], 0),
            ([1], 1),
            ([2, 4], 3),
            ([1, 2, 3], 2),
            ([1, 5, 3, 2], 2.5),
            ([15, 223, 53], 53),
            ([120, 2000, 354, 543], 448.5),
        ]

        for l, r in fixtures:
            self.assertEqual(get_median(l), r)

    def test_get_config(self):

        try:
            config_file = tempfile.NamedTemporaryFile('w', encoding=ENCODING, delete=False)
            with config_file as fp:
                fp.write(json.dumps({
                    "REPORT_SIZE": 100,
                    "LOG_DIR": "./logs",
                    'ERRORS_THRESHOLD': '20%',
                    'LOG_LEVEL': 'DEBUG',
                }))

            fixtures = (
                # (args, result, iserror)
                (None, DEFAULT_CONFIG, False),
                (f'--config {config_file.name}', {
                    "REPORT_SIZE": 100,
                    "REPORT_DIR": "./reports",
                    "LOG_DIR": "./logs",
                    'ERRORS_THRESHOLD': 0.2,
                    'LOG_LEVEL': 'DEBUG',
                }, False),
            )
            ###
            args_start = sys.argv
            for cp, expected, is_error in fixtures:
                """"""
                if cp:
                    if len(sys.argv) > 1:
                        sys.argv = args_start
                    sys.argv.extend(cp.split())

                if is_error:
                    with self.assertRaises(expected) as ex:
                        get_config()
                else:
                    self.assertDictEqual(get_config(), expected)

            #
            conf_list = (
                {'ERRORS_THRESHOLD': '20%'},
                {'ERRORS_THRESHOLD': .2},
            )

            for conf in conf_list:
                config = get_config(conf)
                error_threshold = config.get('ERRORS_THRESHOLD')
                self.assertIsInstance(error_threshold, float)
                self.assertEqual(error_threshold, .2)

        finally:

            try:
                os.unlink(config_file.name)
            except:
                pass

    def test_get_last_log_data(self):
        """"""
        with tempfile.TemporaryDirectory(prefix='test_') as tmpdir:
            config = {
                'LOG_DIR': tmpdir,
            }
            time.sleep(1)

            # директория с логами пустая
            with self.assertRaises(SystemExit):
                get_last_log_data(config)

            fixtures_error = [
                ('apache-access-ui.log-20170628.gz', None, None),
                ('apache-access-ui-log-20170628.gz', None, None),
                ('nginx-access-ui-log-20170628.gz', None, None),
                ('nginx-access-ui.log-20170630.bz2', None, None),
                ('nginx-access-ui.log-20170630.zip', None, None),
                ('nginx-access-ui.log-20170630.rar', None, None),
                ('nginx-access-ui.log-20170630.zg', None, None),
                ('nginx-access-iu.log-20170630.gz', None, None),
                ('nginx-accezz-ui.log-20170630.gz', None, None),
                ('nginx_access_iu.log-20170630.gz', None, None),
                ('ngynx-access-iu.log-20170630.gz', None, None),
                ('nginx-access-ui-log-20170628', None, None),
            ]
            fixtures_date = [
                ('nginx-access-ui.log-20150701.gz', datetime.datetime(2015, 7, 1), '.gz'),
                ('nginx-access-ui.log-20160802', datetime.datetime(2016, 8, 2), ''),
                ('nginx-access-ui.log-20170721', datetime.datetime(2017, 7, 21), ''),
                ('nginx-access-ui.log-20181210.gz', datetime.datetime(2018, 12, 10), '.gz'),
            ]

            for fn, _, _ in fixtures_error:  # заполнение логами
                with open(os.path.join(tmpdir, fn), 'w'):
                    pass

            # среди файлов логов нет подходящего по regex
            with self.assertRaises(SystemExit):
                get_last_log_data(config)

            # по мере создания логов выбирается последний по дате в имени
            for fn, dt, ex in fixtures_date:
                with open(os.path.join(tmpdir, fn), 'w'):
                    pass

                result = get_last_log_data(config)
                self.assertIsInstance(result, tuple)
                d = namedtuple('log_data', 'log_name log_date log_ext')(fn, dt, ex)
                self.assertEqual(result, d)


if __name__ == '__main__':
    unittest.main()
