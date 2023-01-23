#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import logging
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser

from scoring import get_interests, get_score

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
    """"""
    field_type = str

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    def __repr__(self):
        return self.__class__.__name__

    def check(self, value):
        if not value and not self.nullable:
            raise ValueError('Ожидалось не пустое значение')


class CharField(Field):
    """"""
    def check(self, value):
        super().check(value)
        if not value is None and not isinstance(value, str):
            raise ValueError('Ожидалась строка')


class ArgumentsField(Field):
    field_type = dict

    def check(self, value):
        super().check(value)
        if value and not isinstance(value, dict):
            raise ValueError('Ожидался словарь')


class EmailField(CharField):
    def check(self, value):
        super().check(value)
        if value and not '@' in value:
            raise ValueError('Ожидался email')


class PhoneField(Field):
    length = 11
    startswith = '7'

    def check(self, value):
        super().check(value)
        if value and not (len(str(value)) == self.length and str(value).startswith(self.startswith)):
            raise ValueError(
                'Ожидалась строка или число длиной %s и первым символом/числом "%s"' % (self.length, self.startswith))


class DateField(Field):
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
    date_range_years = 70

    def check(self, value):
        super().check(value)
        if value and datetime.datetime.now() - datetime.datetime.strptime(value, self.date_format) > datetime.timedelta(
                days=self.date_range_years * 365):
            raise ValueError('Ожидалась дата рождения не старше %s лет' % self.date_range_years)


class GenderField(Field):
    field_type = int

    def check(self, value):
        super().check(value)
        if value and not value in GENDERS:
            raise ValueError('Ожидалось целое значение из %s' % GENDERS.keys())


class ClientIDsField(Field):
    def check(self, value: list):
        super().check(value)
        if value and not (isinstance(value, list) and len(value) > 0 and all(
                (isinstance(v, int) for v in value))):
            raise ValueError('Ожидался список с целыми числами')
        else:
            pass


class BaseRequest:
    def __init__(self, request: dict = None, ctx: dict = None, store: dict = None):
        self._fields = [f for f in self.__class__.__dict__ if
                        not f.startswith('_') and isinstance(getattr(self.__class__, f), Field)]
        request = request or {}
        self._request_body = request.get('body', None) or request.get('arguments', {})
        self._request_headers = request.get('headers', {})
        self._context = ctx or {}
        self._store = store or {}
        self._error = None

    def __getattribute__(self, item):
        # empty_value_type_map = {
        #     str: '',
        #     int: 0,
        # }
        if item in ('_fields', '_request_body', '__class__'):
            return object.__getattribute__(self, item)
        if item in self._fields:
            request_body = self._request_body
            if item in request_body:
                return request_body.get(item)
            return ''
        return object.__getattribute__(self, item)
        # return object.__getattribute__(self, item)

    @property
    def request_body(self):
        return self._request_body

    @property
    def context(self):
        return self._context

    @property
    def error(self):
        return self._error

    def is_valid(self):
        self.context.setdefault('has', [])
        for field in self._fields:
            field_value = self.request_body.get(field)
            # if field_value:
            #     self.context['has'].append(field)
            cls_attr: Field = getattr(self.__class__, field)
            if cls_attr.required and field not in self.request_body:
                self._error = 'Не указано обязательное поле запроса "%s"' % field
                return False

            try:
                cls_attr.check(field_value)
            except ValueError as e:
                self._error = f'{field}: {e}'
                return False
        return True


class ClientsInterestsRequest(BaseRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def get_response(self):
        response, code = {}, OK
        clients_ids = self.request_body.get('client_ids', [])
        for cid in clients_ids:
            interest = get_interests(None, cid)
            response.setdefault(cid, interest)
        return response, code


class OnlineScoreRequest(BaseRequest):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self):
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

    def get_response(self):
        response, code = {}, OK
        if self._context.get('is_admin', False):
            score = int(ADMIN_SALT)
        else:
            score = get_score(**self.request_body)
        response['score'] = score
        return response, code


class MethodRequest(BaseRequest):
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
    method_request = MethodRequest(request, ctx, store)

    if not method_request.is_valid():
        return method_request.error, INVALID_REQUEST

    if not check_auth(method_request):
        return None, FORBIDDEN

    method_arguments = method_request.get_request_arguments()
    args = {"arguments": method_arguments}

    if method_request.method == 'online_score':
        request_class = OnlineScoreRequest
        ctx['is_admin'] = method_request.is_admin
        ctx['has'] = [k for k in method_request.get_request_arguments()]
    elif method_request.method == 'clients_interests':
        request_class = ClientsInterestsRequest
        ctx['nclients'] = len(method_arguments.get('client_ids', []))
    else:
        return None, INVALID_REQUEST

    _request = request_class(args, ctx, store)
    if _request.is_valid():
        response, code = _request.get_response()
    else:
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
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
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
        # return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
