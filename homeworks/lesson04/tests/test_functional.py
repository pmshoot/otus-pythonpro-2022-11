import hashlib
from datetime import datetime
from functools import partial
from http.server import HTTPServer as BaseHTTPServer
from threading import Thread

import pytest
import requests

from homeworks.lesson04.scoring import api

HTTP_PORT = 8080
BASE_URL = f'http://localhost:{HTTP_PORT}'
URL = f'{BASE_URL}/method/'


class HTTPServer(BaseHTTPServer):
    """
    Class for wrapper to run SimpleHTTPServer on Thread.
        Ctrl +Only Thread remains dead when terminated with C.
    Keyboard Interrupt passes.
    """

    def run(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server_close()


# Блокируем вывод сообщений от сервера в stderr
api.MainHTTPHandler.log_message = lambda *args: ...


@pytest.fixture(scope='module')
def do_request():
    # print("\nStarting server at %s\n" % HTTP_PORT)
    server = HTTPServer(("localhost", HTTP_PORT), api.MainHTTPHandler)
    # Хранилище для обработчика
    server.RequestHandlerClass.store = api.Store()
    # # тестовые данные для кэша хранилища
    server.RequestHandlerClass.store.set('i:1', '["cat", "sport"]')
    server.RequestHandlerClass.store.set('i:3', '["auto", "cooking"]')

    thread = Thread(target=server.run)
    thread.start()

    headers = {'Content-Type': 'application/json'}
    request = partial(requests.request, method='POST', headers=headers)

    yield request

    server.shutdown()
    thread.join()
    print("\nHTTPServer stopped")


@pytest.fixture
def make_request_body():
    request = {
        "login": None,
        "account": "",
        "token": "",
        "method": "",
        "arguments": {}
    }

    def _inner(**kwargs):
        login = kwargs.get('login')
        account = kwargs.get('account', '')
        #
        request['login'] = login
        request['account'] = account
        request['method'] = kwargs.get('method', '')
        request['arguments'] = kwargs.get('arguments', {})
        request['token'] = get_token(login, account)
        return request

    return _inner


def get_token(login, account=""):
    if login == api.ADMIN_LOGIN:
        token = (datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode(encoding=api.ENCODING)
    else:
        token = (account + login + api.SALT).encode(encoding=api.ENCODING)
    return hashlib.sha512(token).hexdigest()


def clean_response(response: requests.Response):
    application_content = response.headers.get('Content-Type')
    assert application_content == 'application/json', 'Ожидался JSON ответ'
    return response.json()


def test_request_structure_invalid(do_request):
    """Тест на наличие обязательных полей запроса"""
    requests_list = [
        {},
        {"account": "", "token": "", "method": "", "arguments": {}},
        {"login": None, "account": "", "method": "", "arguments": {}},
        {"login": None, "account": "", "token": "", "arguments": {}},
        {"login": None, "account": "", "token": "", "method": ""},
    ]

    for request_body in requests_list:
        resp: requests.Response = do_request(json=request_body, url=URL)
        assert resp.status_code == api.INVALID_REQUEST, f"Ожидался код {api.INVALID_REQUEST}"


def test_auth_forbidden(do_request, make_request_body):
    """Тест на невалидную аутентификацию"""
    method = 'online_score'
    login = 'hf'
    account = 'horns&hoofs'

    request_body = make_request_body(login=login, account=account, method=method)
    token = request_body['token'][2:]
    request_body['token'] = token
    resp: requests.Response = do_request(json=request_body, url=URL)
    resp_json = clean_response(resp)
    assert resp.status_code == api.FORBIDDEN, f"Ожидался код {api.FORBIDDEN}"
    assert resp_json == {'code': api.FORBIDDEN, 'error': 'Forbidden'}, f"Ожидался код {api.FORBIDDEN}"


def test_invalid_url_path(do_request, make_request_body):
    """Тест на невалидный URL"""
    method = 'online_score'
    login = 'hf'
    account = 'horns&hoofs'
    url_list = [
        BASE_URL,
        BASE_URL + '/',
        BASE_URL + '/function/',
        BASE_URL + '/method/function/',
        BASE_URL + '/online_score/',
        BASE_URL + '/?method=online_score/',
    ]

    request_body = make_request_body(login=login, account=account, method=method)
    for url in url_list:
        resp: requests.Response = do_request(json=request_body, url=url)
        assert resp.status_code == api.NOT_FOUND, f"Ожидался код {api.NOT_FOUND}"


def test_invalid_request_method(do_request, make_request_body):
    """Тест на невалидный метод запроса"""
    login = 'hf'
    account = 'horns&hoofs'
    method_list = [
        'online_scores',
        'online-scores',
        'get_interests',
        'client_interests',
        'clients_interest',
        'clients interests',
    ]

    for method in method_list:
        request_body = make_request_body(login=login, account=account, method=method)
        resp: requests.Response = do_request(json=request_body, url=URL)
        assert resp.status_code == api.INVALID_REQUEST, f"Ожидался код {api.INVALID_REQUEST}"


def test_online_score_ok(do_request, make_request_body):
    """Тест на валидные значения и результаты метода 'online_score'"""
    method = 'online_score'
    account = 'horns&hoofs'
    arguments_list = [
        ('admin', {"phone": "79175002040", "email": "stupnikov@otus.ru"}, 42, 1),
        ('admin', {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "admin", "last_name": "admin"},
         42, 2),
        ('admin', {"phone": "79175002040", "email": "stupnikov@otus.ru", "birtday": "20.07.2017", "gender": 0}, 42, 3),

        ('hf', {"phone": "79175002040", "email": "stupnikov@otus.ru"}, 3, 4),
        ('hf', {"phone": 79175002040, "email": "stupnikov@otus.ru"}, 3, 5),
        ('hf', {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"}, 2, 6),
        ('hf', {"gender": 0, "birthday": "01.01.2000"}, 0, 7),
        ('hf', {"first_name": "a", "last_name": "b"}, 0.5, 8),
        ('hf', {"phone": "79175002040", "email": "stupnikov@otus.ru"}, 3, 9),
        ('hf', {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
                "first_name": "a", "last_name": "b"}, 5, 10),
    ]

    for login, arguments, exp_score, msg in arguments_list:
        request_body = make_request_body(login=login, account=account, method=method)
        request_body['arguments'] = arguments
        resp: requests.Response = do_request(json=request_body, url=URL)
        resp_json = clean_response(resp)
        assert resp.status_code == api.OK, f"Ожидался код {api.OK} - #{msg}"
        assert 'code' in resp_json.keys(), f'#{msg}'
        assert 'response' in resp_json.keys(), f'#{msg}'
        response = resp_json.get('response')
        assert isinstance(response, dict), f'#{msg}'
        score = response.get('score')
        assert score == exp_score, f'#{msg}'


def test_online_score_invalid(do_request, make_request_body):
    """Тест на не валидные значения и результаты метода 'online_score'"""
    method = 'online_score'
    login = 'hf'
    account = 'horns&hoofs'
    arguments_list = [
        ({}, 1),
        ({"phone": "89175002040", "email": "stupnikov@otus.ru"}, 2),
        ({"phone": "79175002040", "email": "stupnikovotus.ru"}, 3),
        ({"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1}, 4),
        ({"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"}, 5),
        ({"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"}, 6),
        ({"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"}, 7),
        ({"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 8},
         8),
        ({"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"}, 9),
        ({"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
          "first_name": "s", "last_name": 2}, 10),
        ({"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2}, 11),
    ]

    request_body = make_request_body(login=login, account=account, method=method)
    for arguments, msg in arguments_list:
        request_body['arguments'] = arguments
        resp: requests.Response = do_request(json=request_body, url=URL)
        resp_json = clean_response(resp)
        assert resp.status_code == api.INVALID_REQUEST, f"Ожидался код {api.INVALID_REQUEST} - #{msg}"
        assert 'code' in resp_json.keys(), f'#{msg}'
        assert 'error' in resp_json.keys(), f'#{msg}'


def test_clients_interests_ok(do_request, make_request_body):
    """Тест на валидные значения и результаты метода 'clients_interests'"""
    method = 'clients_interests'
    login = 'hf'
    account = 'horns&hoofs'
    arguments_list = [
        ({"client_ids": [1, 2, 3], "date": datetime.today().strftime("%d.%m.%Y")},
         {'1': ['cat', 'sport'], '3': ['auto', 'cooking'], '2': []}, 1),
        ({"client_ids": [1, 2], "date": "19.07.2017"}, {'1': ['cat', 'sport'], '2': []}, 2),
        ({"client_ids": [0]}, {'0': []}, 3),
    ]

    request_body = make_request_body(login=login, account=account, method=method)
    for arguments, expected, msg in arguments_list:
        request_body['arguments'] = arguments
        resp: requests.Response = do_request(json=request_body, url=URL)
        resp_json = clean_response(resp)
        assert resp.status_code == api.OK, f"Ожидался код {api.OK} - #{msg}"
        assert 'code' in resp_json.keys(), f'#{msg}'
        assert 'response' in resp_json.keys(), f'#{msg}'
        response = resp_json.get('response')
        assert isinstance(response, dict), f'#{msg}'
        assert response == expected, f'#{msg}'


def test_clients_interests_invalid(do_request, make_request_body):
    """Тест на не валидные значения и результаты метода 'clients_interests'"""
    method = 'clients_interests'
    login = 'hf'
    account = 'horns&hoofs'
    arguments_list = [
        ({}, 1),
        ({"date": "20.07.2017"}, 2),
        ({"client_ids": [], "date": "20.07.2017"}, 3),
        ({"client_ids": {1: 2}, "date": "20.07.2017"}, 4),
        ({"client_ids": ["1", "2"], "date": "20.07.2017"}, 5),
        ({"client_ids": [1, 2], "date": "XXX"}, 6),
    ]

    request_body = make_request_body(login=login, account=account, method=method)
    for arguments, msg in arguments_list:
        request_body['arguments'] = arguments
        resp: requests.Response = do_request(json=request_body, url=URL)
        resp_json = clean_response(resp)
        assert resp.status_code == api.INVALID_REQUEST, f"Ожидался код {api.INVALID_REQUEST} - #{msg}"
        assert 'code' in resp_json.keys(), f'#{msg}'
        assert 'error' in resp_json.keys(), f'#{msg}'


if __name__ == "__main__":
    pytest.main()
