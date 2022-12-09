import re
import unittest
from pathlib import PurePath


class TestLogAnalizer(unittest.TestCase):
    """"""

    def test_log_regex(self):
        # log_regex = r'.+("(?P<method>GET|POST|HEAD|PUT|OPTIONS) (?P<url>.+) HTTP.+"|"0") (?P<code>\d{3}) (?P<size>\d+) .+" (?P<time>[\d.]+)'
        log_regex = r'.+ (?P<url>"[\w]+ .+ HTTP.+"|"0") (?P<code>\d{3}) (?P<size>\d+) .+" (?P<time>[\d.]+)'
        regex = re.compile(log_regex, re.IGNORECASE)
        log_name = PurePath('./') / 'nginx-access-ui.log-20170601'
        with open(log_name, encoding='UTF-8') as fp:
            for n, line in enumerate(fp):
                matched = regex.match(line)
                self.assertIsNotNone(matched, f'[{n}] {line}, {matched.groupdict()}')
