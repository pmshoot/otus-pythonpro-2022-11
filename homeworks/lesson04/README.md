# Scoring API

## Запуск сервиса

    python3 api.py [-c config_gile.json] [-l log_file] [-p port]

    где:

    -c - полный путь к конфигурационному файлу
    -l - полный путь к лог файлу
    -p - порт сервера для приема соединений

Сервис принимает `POST` запросы с валидным JSON определенного формата по пути `http://<ip-address>/method/` и возвращает
JSON.

---

## Структура JSON запроса

```json
{
  "account": "<имя компании партнера>",
  "login": "<имя >",
  "method": "<имя метода>",
  "token": "<аутентификационный токен>",
  "arguments": {
    "key": "<словарь с аргументами вызываемого метода>"
  }
}
```

- login - строка, обязательно, может быть пустым
- method - строка, обязательно, может быть пустым
- token - строка, обязательно, может быть пустым
- arguments - словарь (объект в терминах json), обязательно, может быть пустым

## Структура ответа

_OK:_

```json
{
  "code": <числовой
  код>,
  "response": {
    <ответ
    вызываемого
    метода>
  }
}
```

_Ошибка:_

```json
{
  "code": <числовой
  код>,
  "error": {
    <сообщение
    об
    ошибке>
  }
}
```

## Аутентификация

В случае если не пройдена, возвращает

```json
{
  "code": 403,
  "error": "Forbidden"
}
```

---

## API Методы

В запросе поля `method` и `arguments`

--- _`online_score`_

аргументы:

- phone - строка или число, длиной 11, начинается с 7, опционально, может быть пустым
- email - строка, в которой есть @, опционально, может быть пустым
- first_name - строка, опционально, может быть пустым
- last_name - строка, опционально, может быть пустым
- birthday - дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет, опционально, может быть пустым
- gender - число 0, 1 или 2, опционально, может быть пустым

_OK:_

```json
{
  "score": <число>
}
```

_Ошибка:_

```json
{
  "code": 422,
  "error": "<сообщение о том какое поле(я) невалидно(ы) и как именно>"
}
```

__Пример__

    $ curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e", "arguments": {"phone": "79991234567", "email": "ast@hf.org", "first_name": "Andy", "last_name": "Moor", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/

    {"code": 200, "response": {"score": 5.0}}

--- _`clients_interests`_

aргументы:

- client_ids - массив числе, обязательно, не пустое
- date - дата в формате DD.MM.YYYY, опционально, может быть пустым

_OK:_

```json
{
  "client_id1": [
    "interest1",
    "interest2"
    ...
  ],
  "client2": [
    ...
  ]
  ...
}
```

_Ошибка:_

```json
{
  "code": 422,
  "error": "<сообщение о том какое поле(я) невалидно(ы) и как именно>"
}
```

__Пример__

    $ curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "admin", "method": "clients_interests", "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c9", "arguments": {"client_ids": [1,2,3,4], "date": "20.07.2017"}}' http://127.0.0.1:8080/method/

    {"code": 200, "response": {"1": ["books", "hi-tech"], "2": ["pets", "tv"], "3": ["travel", "music"], "4": ["cinema", "geek"]}}

## Тесты

Для запуска тестов запустить

```shell
pytest homework/homeworks     
```