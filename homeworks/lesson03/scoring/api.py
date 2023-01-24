#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import logging
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser

from homeworks.lesson03.scoring.scoring import get_interests, get_score

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
    """Базовый класс поля зароса"""
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


class CharField(Field):
    """Текстовая строка"""
    field_type = str

    def check(self, value):
        super().check(value)
        if not value is None and not isinstance(value, self.field_type):
            raise ValueError('Ожидалась строка')


class ArgumentsField(Field):
    """Аргументы для API функций"""
    field_type = dict

    def check(self, value):
        super().check(value)
        if value and not isinstance(value, self.field_type):
            raise ValueError('Ожидался словарь')


class EmailField(CharField):
    """Адрес электронной почты"""

    def check(self, value):
        super().check(value)
        if value and not '@' in value:
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
                'Ожидалась строка или число длиной %s и первым символом/числом "%s"' % (self.length, self.startswith))


class DateField(Field):
    """Дата"""
    field_type = datetime
    date_format = '%d.%m.%Y'

    def check(self, value):
        super().check(value)
        if value and isinstance(value, str):
            try:
                _ = datetime.datetime.strptime(value, self.date_format)
            except ValueError:
                raise ValueError('Ожидался формат даты "%s"' % self.date_format)


class BirthDayField(DateField):
    """Дата дня рождения"""
    date_range_years = 70

    def check(self, value):
        super().check(value)
        if value and datetime.datetime.now() - datetime.datetime.strptime(value, self.date_format) > datetime.timedelta(
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
                    '__class__') or not item in self._fields:  # проверка имен для предотвращения рекурсии
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
            interest = get_interests(None, cid)
            response.setdefault(cid, interest)
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
            score = get_score(**self.request_body)
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


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        data_string = ''
        request = None

        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
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
    (opts, args) = op.parse_args()
    log_file = get_config(opts).get('LOGFILE', opts.log)
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    logging.info("Server stopped")
