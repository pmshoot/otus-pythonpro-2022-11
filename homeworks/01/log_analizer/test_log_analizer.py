import json
import os.path
import re
import sys
import tempfile
import unittest
from pathlib import PurePath

from log_analyzer import get_median, DEFAULT_CONFIG, ENCODING, get_config


class TestLogAnalizer(unittest.TestCase):
    """"""

    def setUp(self) -> None:
        self.config_file = tempfile.NamedTemporaryFile('w', encoding=ENCODING, delete=False)
        with self.config_file as fp:
            fp.write(json.dumps({
                "REPORT_SIZE": 100,
                "LOG_DIR": "./logs",
                'ERRORS_THRESHOLD': '20%',
                'LOG_LEVEL': 'DEBUG',
                }))
        pass

    def tearDown(self) -> None:
        try:
            os.unlink(self.config_file.name)
        except:
            pass

    def test_log_regex(self):
        # log_regex = r'.+("(?P<method>GET|POST|HEAD|PUT|OPTIONS) (?P<url>.+) HTTP.+"|"0") (?P<code>\d{3}) (?P<size>\d+) .+" (?P<time>[\d.]+)'
        log_regex = r'.+ (?P<url>"[\w]+ .+ HTTP.+"|"0") (?P<code>\d{3}) (?P<size>\d+) .+" (?P<time>[\d.]+)'
        regex = re.compile(log_regex, re.IGNORECASE)
        log_name = PurePath('./') / 'nginx-access-ui.log-20170601'
        with open(log_name, encoding='UTF-8') as fp:
            for n, line in enumerate(fp):
                matched = regex.match(line)
                self.assertIsNotNone(matched, f'[{n}] {line}, {matched.groupdict()}')

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

        fixtures = (
            # (args, result)
            (None, DEFAULT_CONFIG, False),
            (f'--config "{self.config_file.name}"', {
                "REPORT_SIZE": 100,
                "REPORT_DIR": "./reports",
                "LOG_DIR": "./logs",
                'ERRORS_THRESHOLD': '20%',
                'LOG_LEVEL': 'DEBUG',
                }, False),
            ('--config lurk.json', FileNotFoundError, True),
            )

        for cp, result, is_error in fixtures:
            """"""
            if cp:
                sys.argv.extend(cp.split())

            if not is_error:
                self.assertEqual(get_config(), result)
            else:
                with self.assertRaises(result):
                    get_config()
