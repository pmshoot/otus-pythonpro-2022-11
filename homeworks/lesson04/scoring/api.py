#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import logging
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser

from homeworks.lesson04.scoring.scoring import get_interests, get_score

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}
ENCODING = 'UTF-8'


class Field(object):
    """Базовый класс поля запроса"""
    field_type = None  # тип данных поля для валидации

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    def __repr__(self):
        return self.__class__.__name__

    def check(self, value):
        """Функция валидации данных поля по заданным критериям"""
        if not value and not self.nullable:
            raise ValueError('Ожидалось не пустое значение')

    def clean(self, value):
        """Приведение значения к типу поля, если отличается"""
        if value and not isinstance(value, self.field_type):
            value = self.field_type(value)
        return value


class CharField(Field):
    """Текстовая строка"""
    field_type = str

    def check(self, value):
        super().check(value)
        if value is not None and not isinstance(value, self.field_type):
            raise ValueError('Ожидалась строка')


class ArgumentsField(Field):
    """Аргументы для API функций"""
    field_type = dict

    def check(self, value):
        super().check(value)
        if value and not isinstance(value, self.field_type):
            raise ValueError('Ожидался словарь')

    def clean(self, value):
        return value


class EmailField(CharField):
    """Адрес электронной почты"""

    def check(self, value):
        super().check(value)
        if value and '@' not in value:
            raise ValueError('Ожидался email')


class PhoneField(Field):
    """Номер телефона"""
    field_type = str
    length = 11
    startswith = '7'

    def check(self, value):
        super().check(value)
        if value and not (len(self.field_type(value)) == self.length
                          and self.field_type(value).startswith(self.startswith)):
            raise ValueError(
                    'Ожидалась строка или число длиной %s и первым символом/числом "%s"' % (
                        self.length, self.startswith))


class DateField(Field):
    """Дата"""
    field_type = datetime.datetime
    date_format = '%d.%m.%Y'

    def check(self, value):
        super().check(value)
        if value:
            try:
                _ = self.clean(value)
            except ValueError:
                raise ValueError('Ожидался формат даты "%s"' % self.date_format)

    def clean(self, value):
        if value and not isinstance(value, self.field_type):
            value = self.field_type.strptime(value, self.date_format)
        return value


class BirthDayField(DateField):
    """Дата дня рождения"""
    date_range_years = 70

    def check(self, value):
        super().check(value)
        if value and datetime.datetime.now() - self.clean(value) > datetime.timedelta(
                days=self.date_range_years * 365):
            raise ValueError('Ожидалась дата рождения не старше %s лет' % self.date_range_years)


class GenderField(Field):
    """Пол человека"""
    field_type = int

    def check(self, value):
        super().check(value)
        if value and not (isinstance(value, self.field_type) and value in GENDERS):
            raise ValueError('Ожидалось целое значение из %s' % GENDERS.keys())


class ClientIDsField(Field):
    """Список ID пользователя"""
    field_type = (list, tuple)

    def check(self, value):
        super().check(value)
        if value and not (isinstance(value, self.field_type) and len(value) > 0 and all(
                (isinstance(v, int) for v in value))):
            raise ValueError('Ожидался список с целыми числами')

    def clean(self, value):
        return value


class BaseRequest:
    """Базовый класс запроса и обработчиков API методов"""

    def __init__(self, request: dict = None, ctx: dict = None, store=None):
        # список имен полей класса описывающих данные запроса или аргументов для API функций
        # формируем через обращение к полям родительского класса
        self._fields = [f for f in self.__class__.__dict__ if
                        not f.startswith('_') and isinstance(getattr(self.__class__, f), Field)]
        request = request or {}
        # сохраняем данные запроса или аргументов API функций
        self._request_body = request.get('body', None) or request.get('arguments', {})
        # заголовки запроса
        self._request_headers = request.get('headers', {})
        # контекст для обработки запросов
        self._context = ctx or {}
        self._store = store
        # описание ошибки при валидации данных
        self._error = None

    def __getattribute__(self, item):
        # при обращении к атрибуту экземпляра класса по имени, совпадающим с именем поля запроса
        # возвращаем данные запроса из словаря _request_body по имени поля или None при отсутствии.
        # доступ к полям описания через родительский класс экземпляра self.__class__

        if item in ('_fields', '_request_body',
                    '__class__') or item not in self._fields:  # проверка имен для предотвращения рекурсии
            return object.__getattribute__(self, item)
        return self._request_body.get(item, None)

    @property
    def request_body(self):
        return self._request_body

    @property
    def context(self):
        return self._context

    @property
    def error(self):
        return self._error

    def is_valid(self) -> bool:
        """Валидация запроса на наличие обязательных полей и данных"""
        self.context.setdefault('has', [])
        for field in self._fields:  # проверка на наличие обязательных полей
            field_value = self.request_body.get(field)  # данные поля запроса
            cls_attr: Field = getattr(self.__class__, field)  # класс описания поля данных запроса
            if cls_attr.required and field not in self.request_body:
                self._error = 'Не указано обязательное поле запроса "%s"' % field
                return False

            try:
                cls_attr.check(field_value)  # валидация данных поля
                # приведение полученного значения к типу поля, если отличается
                if field_value:
                    self.request_body[field] = cls_attr.clean(field_value)
            except ValueError as e:
                self._error = f'{field}: {e}'
                return False
        return True


class ClientsInterestsRequest(BaseRequest):
    """Обработчик API метода 'clients_interests'"""
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def get_response(self) -> tuple[dict, int]:
        response, code = {}, OK
        clients_ids = self.request_body.get('client_ids', [])
        for cid in clients_ids:
            interest = get_interests(self._store, cid)
            response.setdefault(str(cid), interest)
        return response, code


class OnlineScoreRequest(BaseRequest):
    """Обработчик API метода 'online_score'"""
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self) -> bool:
        has = self.context.get('has', [])
        is_valid = super().is_valid()
        has_pairs = any([
            'phone' in has and 'email' in has,
            'first_name' in has and 'last_name' in has,
            'gender' in has and 'birthday' in has
        ])
        if not has_pairs:
            self._error = 'Хотя бы одна пара из phone-email, first name-last name, gender-birthday должна быть с непустыми значениями'

        return is_valid and has_pairs

    def get_response(self) -> tuple[dict, int]:
        response, code = {}, OK
        if self._context.get('is_admin', False):
            score = int(ADMIN_SALT)
        else:
            score = get_score(self._store, **self.request_body)
        response['score'] = score
        return response, code


class MethodRequest(BaseRequest):
    """Запрос, с указанием API метода, аргументов и авторизации пользователя"""
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

    def get_request_arguments(self):
        return self.arguments or {}


def check_auth(method_request):
    """Проверка авторизации пользователя"""
    if method_request.is_admin:
        token = (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode(encoding=ENCODING)
        digest = hashlib.sha512(token).hexdigest()
    else:
        token = (method_request.account + method_request.login + SALT).encode(encoding=ENCODING)
        digest = hashlib.sha512(token).hexdigest()
    if digest == method_request.token:
        return True
    return False


def method_handler(request, ctx, store):
    """Обработка данных запроса, возврат результата и кода выполнения"""
    method_request = MethodRequest(request, ctx, store)

    # проверка на валидность переданных в запросе данных
    if not method_request.is_valid():
        logging.error('Invalid request %s' % method_request.error)
        return method_request.error, INVALID_REQUEST

    # авторизация пользователя
    if not check_auth(method_request):
        logging.error("Login '%s' auth error" % method_request.login)
        return None, FORBIDDEN

    method_arguments = method_request.get_request_arguments()  # аргументы, переданные в запросе для API метода

    # определение метода API и вызов функции get_response() соответствующего класса
    if method_request.method == 'online_score':
        request_class = OnlineScoreRequest
        ctx['is_admin'] = method_request.is_admin
        ctx['has'] = [k for k in method_request.get_request_arguments()]
    elif method_request.method == 'clients_interests':
        request_class = ClientsInterestsRequest
        ctx['nclients'] = len(method_arguments.get('client_ids', []))
    else:
        # wrong API method
        logging.error('Invalid request method %s' % method_request.method)
        return None, INVALID_REQUEST

    # класс запроса согласно API метода
    _request = request_class({"arguments": method_arguments}, ctx, store)

    # проверка на валидность аргументов для API метода
    if _request.is_valid():
        response, code = _request.get_response()
    else:
        logging.error('%s: invalid request %s' % (method_request.method, method_request.error))
        response, code = _request.error, INVALID_REQUEST

    return response, code


class LocalStorage:
    """"""

    def __init__(self, *args, **kwargs):
        self._store = dict()
        self.args = args
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key, value):
        self._store[key] = value

    def delete(self, key):
        del self._store[key]


class Store:
    """"""
    default_timeout = 5
    default_max_retry = 1

    def __init__(self, uri=None, user=None, passw=None, timeout=None, max_retry=None):
        """"""
        self.uri = uri
        self.timeout = timeout or self.default_timeout
        self.max_retry = max_retry or self.default_max_retry
        #
        self._cache = {}
        self._store = self.get_store_connection(uri, user=user, passw=passw)

    def get_server_address(self, uri):
        try:
            stype, saddr, sport = uri.split(':')
            return stype, (saddr.lstrip('//'), sport.rstrip('/'))
        except ValueError:
            raise ValueError('Адрес сервера должен быть в виде "server_type://server_address:server_port/..."')

    def get_store_connection(self, uri, user=None, passw=None):
        """"""
        if not uri:
            return LocalStorage()

        stype, conn_data = self.get_server_address(uri)

        if stype == 'redis':
            return self._get_redis_connection(*conn_data, user=user, passw=passw)

        if stype == 'memcache':
            return self._get_memcache_connection(conn_data)

        if stype == 'tarantool':
            return self._get_tarantool_connection(*conn_data, user=user, passw=passw)

        raise ValueError('Не распознан тип кеширующего севера')

    def _get_redis_connection(self, addr, port, user, passw):
        """"""
        try:
            import redis
            from redis.retry import Retry
            from redis.backoff import ExponentialBackoff
        except ImportError:
            raise ImportError('Не найден пакет redis')

        retry = Retry(ExponentialBackoff(), self.max_retry)

        storage = redis.Redis(host=addr,
                              port=port,
                              retry=retry,
                              username=user,
                              password=passw,
                              socket_connect_timeout=self.timeout,
                              )
        return storage

    def _get_memcache_connection(self, conn_data: tuple, user, passw):
        """"""
        try:
            from pymemcache.client.base import Client
            from pymemcache.client.retrying import RetryingClient
            from pymemcache.exceptions import MemcacheUnexpectedCloseError
        except ImportError:
            raise ImportError('Не найден пакет pymemcache')

        base_client = Client(conn_data, timeout=self.timeout)
        storage = RetryingClient(base_client,
                                 attempts=self.max_retry,
                                 retry_delay=0.01,
                                 retry_for=[MemcacheUnexpectedCloseError],
                                 )
        return storage

    def _get_tarantool_connection(*conn_data, user=None, passw=None):
        raise NotImplementedError('Требуется реализация диалекта tarantool select')

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value):
        self._store.set(key, value)

    def cache_get(self, key):
        """"""
        value, timestamp = self._cache.get(key, (None, None))
        if value and not timestamp:  # ttl не установлен, храним "вечно"
            return value
        if timestamp and (timestamp < datetime.datetime.now().timestamp()):  # ttl "протух", удаляем key-value
            del self._cache[key]
            value = None
        return value

    def cache_set(self, key, value, cache_ttl=None):
        if cache_ttl is not None and not isinstance(cache_ttl, (int, float)):
            raise ValueError('Значение времени жизни кэша должно быть int или float')
        if not isinstance(key, (int, float, str)):
            raise ValueError('Значение ключа кэша должно быть int, float, str')
        timestamp = (datetime.datetime.now() + datetime.timedelta(0, cache_ttl)).timestamp() if cache_ttl else None
        self._cache[key] = value, timestamp


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):  # pragma: no cover
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        data_string = ''
        request = None

        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except Exception:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    # ищем и вызываем функцию, согласно url пути
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                logging.info("Wrong url path: %s" % self.path)
                code = NOT_FOUND
        else:
            code = INVALID_REQUEST

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode(ENCODING))


def get_config(opts) -> dict:
    """Читает конфигурацию из файла, если указан в командной строке"""
    config = {}
    if opts.config:
        # читаем, парсим конфиг файл
        try:
            with open(opts.config, encoding=ENCODING) as fp:
                config.update(json.load(fp))
                logging.info('Load config from file: %s' % opts.config)
        except (FileNotFoundError, FileExistsError):
            logging.error('Config file not found')
    return config


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-c", "--config", default=None, help="Файл конфигурации json")
    op.add_option("-s", "--store", default=None, help="Адрес хранилища")
    (opts, args) = op.parse_args()
    log_file = get_config(opts).get('LOGFILE', opts.log)
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    MainHTTPHandler.store = Store(opts.store)
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    logging.info("Server stopped")
