import datetime
import functools
import hashlib
import time
import unittest

from homeworks.lesson04.scoring import api


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)

        return wrapper

    return decorator


class TestFields(unittest.TestCase):
    """Тесты полей запроса"""

    @cases([
        (False, False, None, 'Field None'),
        (False, False, '', 'Field ""'),
        (False, False, [], 'Field []'),
    ])
    def test_base_field_not_nullable(self, required, nullable, value, msg):
        f = api.Field(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, True, 1, 'Raise on nullable base field with 1'),
        (False, True, None, 'Raise on nullable base field with None'),
    ])
    def test_base_field_nullable(self, required, nullable, value, msg):
        f = api.Field(required=required, nullable=nullable)
        try:
            f.check(value)
        except ValueError:
            assert False, ''

    @cases([
        (False, False, 1, 'CharField: 1'),
        (False, False, 1.3, 'CharField: 1.3'),
        (False, False, ('qwerty',), 'CharField: ("qwerty",)'),
    ])
    def test_char_field(self, required, nullable, value, msg):
        f = api.CharField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, False, 'data', 'ArgumentsField'),
        (False, False, 1, 'ArgumentsField'),
        (False, False, ('qwerty',), 'ArgumentsField'),
    ])
    def test_argument_field(self, required, nullable, value, msg):
        f = api.ArgumentsField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, False, 'some.server.ru', 'EmailField'),
        (False, False, 'mymail#server.com', 'EmailField'),
    ])
    def test_email_field(self, required, nullable, value, msg):
        f = api.EmailField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, False, '89175002040', 'PhoneField'),
        (False, False, '891750020', 'PhoneField'),
        (False, False, '7123456789', 'PhoneField'),
        (False, False, '712345678902', 'PhoneField'),
    ])
    def test_phone_field(self, required, nullable, value, msg):
        f = api.PhoneField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, False, '2020.02.23', 'DateField'),
        (False, False, '01-01-2020', 'DateField'),
        (False, False, '01/01/2020', 'DateField'),
    ])
    def test_date_field(self, required, nullable, value, msg):
        f = api.DateField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, False, '01/01/1090', 'BirthDayField'),
        (False, False, '01/01/2090', 'BirthDayField'),
    ])
    def test_birth_date_field(self, required, nullable, value, msg):
        f = api.BirthDayField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, False, '0', 'GenderField'),
        (False, False, 1.0, 'GenderField'),
        (False, False, -1, 'GenderField'),
        (False, False, 100, 'GenderField'),
        (False, False, '100', 'GenderField'),
    ])
    def test_gender_field(self, required, nullable, value, msg):
        f = api.GenderField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)

    @cases([
        (False, False, 100, 'ClientIDsField'),
        (False, False, [], 'ClientIDsField'),
        (False, False, ('1', '0', '1'), 'ClientIDsField'),
        (False, False, (1.0, 0, 2), 'ClientIDsField'),
    ])
    def test_client_id_field(self, required, nullable, value, msg):
        f = api.ClientIDsField(required=required, nullable=nullable)
        with self.assertRaises(ValueError, msg=msg):
            f.check(value)


class TestLocalStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = api.LocalStorage()
        self.storage._store['key'] = 'value'

    def test_set(self):
        self.storage.set('num', 1)
        self.assertTrue('num' in self.storage._store.keys())
        self.assertEqual(self.storage._store['num'], 1)

    def test_get(self):
        value = self.storage.get('key')
        self.assertEqual(value, 'value')

    def test_delete(self):
        self.storage.delete('key')
        self.assertTrue('key' not in self.storage._store.keys())


class TestStore(unittest.TestCase):
    """"""

    def get_mock_connection(self, s_type, *args, **kwargs):
        st = api.LocalStorage(*args, **kwargs)
        st.s_type = s_type
        return st

    def setUp(self) -> None:
        self._store = api.Store()
        self._store._get_redis_connection = functools.partial(self.get_mock_connection, 'redis')
        self._store._get_memcache_connection = functools.partial(self.get_mock_connection, 'memcache')
        self._store._get_tarantool_connection = functools.partial(self.get_mock_connection, 'tarantool')

    @cases([
        ("https://localhost:1234/", 'https', 'localhost', '1234'),
        ("memcache://localhost:5656/", 'memcache', 'localhost', '5656'),
        ("redis://address.local.domain:5656/", 'redis', 'address.local.domain', '5656'),
    ])
    def test_ok_get_server_address(self, *data):
        uri, exp_stype, exp_saddr, exp_sport = data
        stype, addr = self._store.get_server_address(uri)
        self.assertIsInstance(addr, tuple)
        saddr, sport = addr
        self.assertEqual(stype, exp_stype)
        self.assertEqual(saddr, exp_saddr)
        self.assertEqual(sport, exp_sport)

    @cases([
        "https:\\localhost.1234/",
        "memcache://localhost/",
        "address.local.domain:5656/",
    ])
    def test_invalid_get_server_address(self, uri):
        with self.assertRaises(ValueError):
            _, _ = self._store.get_server_address(uri)

    @cases([
        "https://localhost:1234/",
        "memcached://localhost:5555/",
        "rеdis://local.domain:1234",
        "tarantol://local.domain.ext:1234",
    ])
    def test_error_get_connection(self, uri):
        _ = self._store.get_server_address(uri)
        with self.assertRaises(ValueError):
            self._store.get_store_connection(uri)

    @cases([
        ("", None),
        ("memcache://localhost:5555/", 'memcache'),
        ("redis://local.domain:1234", 'redis'),
        ("tarantool://local.domain.ext:1234", 'tarantool'),
    ])
    def test_ok_get_connection(self, *data):
        uri, stype = data
        storage = self._store.get_store_connection(uri)
        self.assertIsInstance(storage, api.LocalStorage)
        if stype:
            self.assertEqual(storage.s_type, stype)

    @cases([
        (1, 'some_data', 10.0),
        ('12', 'and_more_data', None),
        (1233212123, 123, 100),
    ])
    def test_store_cache_ok_set(self, *data):
        key, value, cache_ttl = data
        self._store.cache_set(key, value, cache_ttl)
        self.assertIn(key, self._store._cache.keys())
        val, timestamp = self._store._cache[key]
        self.assertEqual(val, value)
        if cache_ttl:
            self.assertTrue(timestamp > datetime.datetime.now().timestamp())
        else:
            self.assertIsNone(timestamp)

    @cases([
        (1, 'some_data', ''),
        (2, 'more_data', '23'),
        ('12', 'and_more_data', int),
        (None, 'and_more_data', 1.0),
        (str, 'and_more_data', 12),
    ])
    def test_store_cache_invalid_set(self, *data):
        key, value, cache_ttl = data
        with self.assertRaises(ValueError):
            self._store.cache_set(key, value, cache_ttl)

    @cases([
        {'set': ('12', 'data', None), 'wait': 2, 'expected': 'data'},
        {'set': (1, 'some_data', 1), 'wait': 2, 'expected': None},
        {'set': (1233212123, 123, 100), 'wait': 2, 'expected': 123},
    ])
    def test_store_cache_get(self, data):
        key, value, cache_ttl = data['set']
        wait = data['wait']
        expected = data['expected']
        self._store.cache_set(key, value, cache_ttl)
        time.sleep(wait)
        val = self._store.cache_get(key)
        self.assertEqual(expected, val)


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = api.Store()
        self.store.set('i:1', '["cat", "sport"]')
        self.store.set('i:3', '["auto", "cooking"]')

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    def set_valid_auth(self, request):
        encoding = 'UTF-8'
        if request.get("login") == api.ADMIN_LOGIN:
            token = (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode(encoding=encoding)
        else:
            token = (request.get("account", "") + request.get("login", "") + api.SALT).encode(encoding=encoding)
        request["token"] = hashlib.sha512(token).hexdigest()

    def test_empty_request(self):
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments": {}},
    ])
    def test_bad_auth(self, do_request):
        _, code = self.get_response(do_request)
        self.assertEqual(api.FORBIDDEN, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
        {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
        {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
    ])
    def test_invalid_method_request(self, do_request):
        self.set_valid_auth(do_request)
        response, code = self.get_response(do_request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertTrue(len(response))

    @cases([
        {},
        {"phone": "79175002040"},
        {"phone": "89175002040", "email": "stupnikov@otus.ru"},
        {"phone": "79175002040", "email": "stupnikovotus.ru"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "s", "last_name": 2},
        {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"},
        {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
    ])
    def test_invalid_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        ({"phone": "79175002040", "email": "stupnikov@otus.ru"}, 3),
        ({"phone": 79175002040, "email": "stupnikov@otus.ru"}, 3),
        ({"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"}, 2),
        ({"gender": 0, "birthday": "01.01.2000"}, 0),
        ({"gender": 2, "birthday": "01.01.2000"}, 1.5),
        ({"first_name": "a", "last_name": "b"}, 0.5),
        ({"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
          "first_name": "a", "last_name": "b"}, 5),
    ])
    def test_ok_score_request(self, *data):
        arguments, excpected_score = data
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, 'Ожидался код 200')
        score = response.get("score")
        self.assertEqual(excpected_score, score)
        self.assertTrue(isinstance(score, (int, float)) and score >= 0)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()),
                         'Контекст has не соответствует не пустым полям')

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        score = response.get("score")
        self.assertEqual(score, 42)

    @cases([
        {},
        {"date": "20.07.2017"},
        {"client_ids": [], "date": "20.07.2017"},
        {"client_ids": {1: 2}, "date": "20.07.2017"},
        {"client_ids": ["1", "2"], "date": "20.07.2017"},
        {"client_ids": [1, 2], "date": "XXX"},
    ])
    def test_invalid_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        ({"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
         {'1': ['cat', 'sport'], '3': ['auto', 'cooking'], '2': []}),
        ({"client_ids": [1, 2], "date": "19.07.2017"}, {'1': ['cat', 'sport'], '2': []}),
        ({"client_ids": [0]}, {'0': []}),
    ])
    def test_ok_interests_request(self, *data):
        arguments, exp_interests = data
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertDictEqual(response, exp_interests)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(isinstance(v, list) and all(isinstance(i, str) for i in v)
                            for v in response.values()))
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))

    def test_wrong_method(self):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_requests", "arguments": {}}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertIsNone(response)


if __name__ == "__main__":
    unittest.main()
