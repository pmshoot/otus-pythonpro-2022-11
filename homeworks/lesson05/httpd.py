import argparse
import datetime
import io
import logging
import os
import posixpath
import re
import shutil
import socket
import threading
import time

# status codes
OK = 200, 'OK', 'Request fulfilled, document follows'
BAD_REQUEST = 400, 'Bad Request', 'Bad request syntax or unsupported method'
FORBIDDEN = 403, 'Forbidden', 'Request forbidden -- authorization will not help'
NOT_FOUND = 404, 'Not Found', 'Nothing matches the given URI'
METHOD_NOT_ALLOWED = 405, 'Method Not Allowed', 'Specified method is invalid for this resource'
INTERNAL_SERVER_ERROR = 500, 'Internal Server Error', 'Server got itself in trouble'

DEFAULT_PORT = 8080
DEFAULT_DOCUMENT_ROOT = os.getcwd()
DEFAULT_WORKERS = 1
ALLOWED_REQUESTS = 'get', 'head'

_hexdig = '0123456789ABCDEFabcdef'
_hextobyte = None
extensions_map = _encodings_map_default = {
    '.html': 'text/html',
    '.htm': 'text/html',
    '.css': 'text/css',
    '.js': 'text/javascript',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.swf': 'application/x-shockwave-flash',
    '.gz': 'application/gzip',
    '.Z': 'application/octet-stream',
    '.bz2': 'application/x-bzip2',
    '.xz': 'application/x-xz',
}


def date_time_string(timestamp=None):
    """"""
    if not timestamp:
        timestamp = time.time()
    dt = datetime.datetime.fromtimestamp(timestamp)
    timetuple = dt.timetuple()
    if dt.tzinfo is None:
        zone = '-0000'
    else:
        zone = dt.strftime("%z")

    date_time_string = '%s, %02d %s %04d %02d:%02d:%02d %s' % (
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][timetuple[6]],
        timetuple[2],
        ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][timetuple[1] - 1],
        timetuple[0], timetuple[3], timetuple[4], timetuple[5],
        zone)

    return date_time_string


class HTTPServer:
    """"""
    server_version = "OTUServer/0.1"
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    allow_reuse_address = False
    timeout = None

    def __init__(self, address: tuple[str, int], **kwargs):
        """"""
        self.address = self.get_address(*address)
        self.socket = socket.socket(self.address_family, self.socket_type)
        self.is_shut_down = threading.Event()
        self.shutdown_request = False
        self.workers = kwargs.get('workers', DEFAULT_WORKERS)
        self.logger = kwargs.get('logger') or logging.getLogger('httpd')
        # self._threads = []

        self.root_dir = kwargs.get('root_dir', DEFAULT_DOCUMENT_ROOT)
        self.handler_class = RequestHandler

        self.activate()

    def __del__(self):
        self.close()

    def close(self):
        try:
            # self.logger.debug(f'shutdown socket: {self.socket.shutdown(socket.SHUT_WR)}')
            # self.logger.debug(f'close socket: {self.socket.close()}')
            self.socket.close()
            self.logger.info(f'{self.server_version} stopped')
        except Exception as err:
            logger.error(f'exception on close socket: {err}')
            pass

    def get_address(self, *args):
        infos = socket.getaddrinfo(*args)
        for family, type, proto, canonname, sockaddr in infos:
            if family == socket.AF_INET and type == socket.SOCK_STREAM:
                return sockaddr
        raise ValueError('Не определен тип сокета')

    def activate(self):
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.address)
        host, port = self.address
        self.server_name = socket.gethostbyaddr(host)
        self.server_port = port
        # self.socket.listen(self.workers)
        self.socket.listen(1)
        self.logger.info(f'{self.server_version} listen at {host}:{port}')

    def serve_forever(self):
        self.is_shut_down.clear()
        try:
            while not self.shutdown_request:
                # if self.shutdown_request:
                #     break
                self.process_request(*self.socket.accept())
        finally:
            self.shutdown_request = False
            self.is_shut_down.set()

    def shutdown(self):
        self.shutdown_request = True
        self.close()
        # self.is_shut_down.wait()

    def _process_request_thread(self, sock, client_addr):
        try:
            self.handler_class(sock, client_addr, self)
        except Exception as e:
            print(e)
            # self.handle_error(sock, client_addr)

    def process_request(self, sock, client_addr):
        saddr, sport = client_addr
        self.logger.info(f'Accepted connection from {saddr}:{sport}')
        t = threading.Thread(target=self._process_request_thread,
                             args=(sock, client_addr))
        t.daemon = True
        # self._threads.append(t)
        t.start()


class RequestHandler:
    """"""
    protocol_version = 'HTTP/1.1'
    default_error_content_type = "text/html;charset=utf-8"
    rbufsize = None
    wbufsize = None
    max_request_line_size = 64 * 1024
    max_headers = 100
    index_files = "index.html", "index.htm"

    error_message = """\
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
    <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
            <title>Error</title>
        </head>
        <body>
            <h1>%(code)d</h1>
            <p>%(message)s.</p>
            <p>%(code)s - %(explain)s.</p>
        </body>
    </html>
    """

    def __init__(self, sock: socket, client_addr, server):
        self.sock = sock
        self.client_addr = client_addr
        self.server = server

        self.rfile = self.sock.makefile('rb', self.rbufsize)
        self.wfile = self.sock.makefile('wb', self.wbufsize)

        self.headers_buffer = []
        self.close_conn = False
        self.raw_request = None
        self.request = ""
        self.request_version = ""
        self.request_command = ""
        self.request_path = ""
        self.request_headers = {}
        self.logger = server.logger.getChild(f'w-{id(self)}')

        self.process()

    def __del__(self):
        if self.wfile:
            self.wfile.close()
            # self.logger.debug('closed socket.wfile')
        if self.rfile:
            self.rfile.close()
            # self.logger.debug('closed socket.rfile')



    def process(self):
        try:
            while not self.close_conn:
                self.handle_request()
        finally:
            if not self.wfile.closed:
                try:
                    self.wfile.flush()
                except socket.error:
                    pass

    def handle_request(self):
        """"""
        try:
            self.raw_request = self.rfile.readline(self.max_request_line_size + 1)
            self.logger.debug(f'w-{id(self)} get request: {self.raw_request.decode()}')
            if not self.raw_request:
                self.close_conn = True
                return

            if len(self.raw_request) > self.max_request_line_size:
                self.request = ""
                self.request_version = ""
                self.request_command = ""
                self.request_headers = {}
                self.send_error(*BAD_REQUEST)
                return

            if not self.parse_request():
                self.close_conn = True
                return

            if self.request_command.lower() not in ALLOWED_REQUESTS:
                self.send_error(*METHOD_NOT_ALLOWED)
                return

            handle_method = getattr(self, self.request_command.lower())
            handle_method()

            try:
                self.wfile.flush()
            except socket.error:
                pass

        except socket.timeout:
            self.close_conn = True

    def send_error(self, code, message=None, explain=None):
        """"""
        content = (self.error_message % {
            'code': code,
            'message': message or '???',
            'explain': explain or '???'
        }).encode('UTF-8', 'replace')

        self.init_headers(code, message)
        self.add_header('Connection', 'close')
        self.add_header('Content-Type', 'text/html;charset=utf-8')
        self.add_header('Content-Length', str(len(content)))
        self.end_headers()

        if self.request_command != 'HEAD':
            self.wfile.write(content)
        self.wfile.flush()

    def init_headers(self, code, message='', explain=''):
        """"""
        self.headers_buffer.append(
                ("%s %d %s\r\n" % (self.protocol_version, code, message)).encode('latin-1', 'strict')
        )
        self.add_header('Server', self.server.server_version)
        self.add_header('Date', date_time_string())

    def add_header(self, keyword: str, value: str):
        """"""
        self.headers_buffer.append(
                ("%s: %s\r\n" % (keyword, value)).encode('latin-1', 'strict'))

        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_conn = True
            elif value.lower() == 'keep-alive':
                self.close_conn = False

    def end_headers(self):
        """"""
        self.headers_buffer.append(b"\r\n")
        self.wfile.write(b"".join(self.headers_buffer))
        self.headers_buffer = []

    def parse_request(self):
        """"""
        self.close_conn = True
        request = str(self.raw_request, 'iso-8859-1')
        request = request.rstrip('\r\n')
        self.request = request
        words = request.split()
        if len(words) == 0:
            return False
        if len(words) >= 3:  # Enough to determine protocol version
            version = words[-1]
            try:
                if not version.startswith('HTTP/'):
                    raise ValueError
                base_version_number = version.split('/', 1)[1]
                version_number = base_version_number.split(".")
                if len(version_number) != 2:
                    raise ValueError
                version_number = int(version_number[0]), int(version_number[1])
            except (ValueError, IndexError):
                self.send_error(
                        *BAD_REQUEST[:2],
                        "Bad request version (%r)" % version,
                )
                return False
            if version_number >= (1, 1) and self.protocol_version >= "HTTP/1.1":
                self.close_conn = False
            if version_number >= (2, 0):
                self.send_error(
                        *BAD_REQUEST[:2],
                        "Invalid HTTP version (%s)" % base_version_number)
                return False

            self.request_version = version

        if not 2 <= len(words) <= 3:
            self.send_error(
                    *BAD_REQUEST[:2],
                    "Bad request syntax (%r)" % request)
            return False

        self.request_command, self.request_path = words[:2]

        if self.request_path.startswith('//'):
            self.request_path = '/' + self.request_path.lstrip('/')  # Reduce to a single /

        try:
            self._read_headers(self.rfile)
        except ValueError as err:
            self.send_error(
                    *BAD_REQUEST[:2],
                    str(err),
            )
            return False

        conn_type = self.request_headers.get('Connection', "")
        if conn_type.lower() == 'close':
            self.close_conn = True
        elif (conn_type.lower() == 'keep-alive' and
              self.protocol_version >= "HTTP/1.1"):
            self.close_conn = False
        return True

    def _read_headers(self, fp):
        """"""
        headers = []
        while True:
            line = fp.readline(self.max_request_line_size + 1)
            if len(line) > self.max_request_line_size:
                raise ValueError("Too long header line")
            headers.append(line)
            if len(headers) > self.max_headers:
                raise ValueError("Too many headers")
            if line in (b'\r\n', b'\n', b''):
                break
        for line in headers:
            line = line.rstrip(b'\r\n').decode('latin-1')
            value = line.split(':')
            if len(value) != 2:
                continue
            self.request_headers[value[0]] = value[1]

    def get(self):
        """"""
        f = self.make_response()
        if f:
            try:
                shutil.copyfileobj(f, self.wfile)
            finally:
                f.close()

    def head(self):
        """"""
        f = self.make_response()
        if f:
            f.close()

    def make_response(self):
        """"""
        path = self.translate_path(self.request_path)
        f = None
        if os.path.isdir(path):
            for index in self.index_files:
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                self.send_error(*NOT_FOUND)
                return

        if path.endswith("/"):  # path to file w/trailing
            self.send_error(*NOT_FOUND)
            return

        if os.path.exists(path):
            mime_type = self.get_mime_type(path)
            try:
                f = open(path, 'rb')
                fp = os.fstat(f.fileno())
                self.init_headers(*OK)
                self.add_header("Content-type", mime_type)
                self.add_header("Content-Length", str(fp[6]))
                self.add_header("Last-Modified", date_time_string(fp.st_mtime))
                self.end_headers()
                return f

            except Exception as err:
                if f:
                    f.close()
                self.send_error(
                        *INTERNAL_SERVER_ERROR[:2],
                        str(err)  # todo ошибку в лог, в ответ общее описание
                )
        else:
            self.send_error(*NOT_FOUND)

    def translate_path(self, path: str):
        """"""
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        has_trailing_slash = path.rstrip().endswith('/')
        if '%' in path:
            # encode string
            path = path.encode('utf-8')
            chunks = path.split(b'%')
            res = [chunks[0]]
            global _hextobyte
            if _hextobyte is None:
                _hextobyte = {(a + b).encode(): bytes.fromhex(a + b) for a in _hexdig for b in _hexdig}

            for chunk in chunks[1:]:
                try:
                    res.append(_hextobyte[chunk[:2]])
                    res.append(chunk[2:])
                except KeyError:
                    res.append(b'%')
                    res.append(chunk)
            path = (b''.join(res)).decode('utf-8')

        #
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        spath = os.path.abspath(self.server.root_dir)
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                continue
            spath = os.path.join(spath, word)
        if has_trailing_slash:
            spath += '/'
        return spath

    def get_mime_type(self, path):
        """"""
        _, ext = posixpath.splitext(path)
        return extensions_map.get(ext.lower(), 'application/octet-stream')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', '-w', type=int, default=DEFAULT_WORKERS,
                        help=f'количество обслуживающих потоков (default: {DEFAULT_WORKERS})')
    parser.add_argument('--bind', '-b', metavar='ADDRESS',
                        help='адрес прослушивания сервером (default: все доступные интерфейсы)')
    parser.add_argument('--root', '-r', metavar='DOCUMENT_ROOT', default=DEFAULT_DOCUMENT_ROOT,
                        help='путь к каталогу с HTML (default: текущая директория)')
    parser.add_argument('--debug', '-d', default=False, action=argparse.BooleanOptionalAction,
                        help='режим отладки')
    parser.add_argument('--quiet', '-q', default=False, action=argparse.BooleanOptionalAction,
                        help='режим отладки')
    parser.add_argument('port', action='store', default=DEFAULT_PORT, type=int, nargs='?',
                        help=f'порт  (default: {DEFAULT_PORT})')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    if args.quiet:
        logging.disable(logging.INFO)
    logger = logging.getLogger('httpd')
    if args.debug:
        logger.setLevel(logging.DEBUG)

    server = HTTPServer((args.bind, args.port), root_dir=args.root, workers=args.workers, logger=logger)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
