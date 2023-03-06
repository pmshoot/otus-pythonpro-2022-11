## OTUServer

### Сервер httpd.py спроектирован на theads pool.

### Нагрузочное тестирование

Тесты проведены программой `wrk` (с `ab` не сложилось, по причине зависания программы по окончании тестов, что заняло
тонну времени на выяснение причин и перебора кода сервера, пока не выявился виновник проблемы)

Параметры запуска `wrk`:

```shell
wrk -c 100 -d 30 -t 1  http://127.0.0.1:8080
```

- соединений:          100
- threads:            1
- продолжительность:  30c

1. С одним рабочим тредом и выводом информации на консоль:

```shell
>python httpd.py 8080
Running 30s test @ http://127.0.0.1:8080
  1 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     5.70ms   53.73ms   1.66s    99.02%
    Req/Sec     1.84k   140.68     1.98k    91.84%
  53859 requests in 30.02s, 29.48MB read
  Socket errors: connect 0, read 0, write 0, timeout 7
  Non-2xx or 3xx responses: 53859
Requests/sec:   1793.97
Transfer/sec:      0.98MB
```

2. 1 thread, тихий режим - без вывода на консоль

```shell
>python httpd.py -q 8080 
Running 30s test @ http://127.0.0.1:8080
  1 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     4.73ms   50.72ms   1.65s    99.11%
    Req/Sec     2.52k   174.39     2.68k    96.99%
  75167 requests in 30.02s, 41.15MB read
  Socket errors: connect 0, read 0, write 0, timeout 5
  Non-2xx or 3xx responses: 75167
Requests/sec:   2503.74
Transfer/sec:      1.37MB
``` 

3. 4 threads, тихий режим - без вывода на консоль

```shell
>python httpd.py -q -w 4 8080
Running 30s test @ http://127.0.0.1:8080
  1 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     8.96ms   60.17ms   1.66s    98.25%
    Req/Sec     2.22k   109.53     2.36k    90.00%
  66301 requests in 30.03s, 36.29MB read
  Socket errors: connect 0, read 0, write 0, timeout 20
  Non-2xx or 3xx responses: 66301
Requests/sec:   2208.11
Transfer/sec:      1.21MB
```

4. 10 threads, тихий режим - без вывода на консоль

```shell
>python httpd.py -q -w 10 8080
Running 30s test @ http://127.0.0.1:8080
  1 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    13.26ms   69.44ms   1.66s    97.95%
    Req/Sec     2.18k    48.21     2.29k    77.33%
  64985 requests in 30.03s, 35.57MB read
  Socket errors: connect 0, read 0, write 0, timeout 21
  Non-2xx or 3xx responses: 64985
Requests/sec:   2164.28
Transfer/sec:      1.18MB
``` 

5. 50 threads, тихий режим - без вывода на консоль

```shell
>python httpd.py -q -w 50 8080
Running 30s test @ http://127.0.0.1:8080
  1 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    28.53ms   50.41ms   1.68s    98.90%
    Req/Sec     2.12k    41.09     2.23k    72.67%
  63210 requests in 30.02s, 34.60MB read
  Socket errors: connect 0, read 0, write 0, timeout 2
  Non-2xx or 3xx responses: 63210
Requests/sec:   2105.68
Transfer/sec:      1.15MB
```

По мере увеличения кол-ва рабочих тредов, скорость обработки уменьшается. Возможно связано с GL.
Самым быстрым оказался вариант с 1 тредом и без вывода информации по мере обработки запросов сервером на консоль.
