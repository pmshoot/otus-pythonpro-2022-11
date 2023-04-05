# Hasker

### Сервис вопросов и ответов для самых обездоленных

Разверстка: 
1. создается контейнер с маппингом 80 порта контейнера на 8000 хоста: 
```shell
docker run --rm -it -p 8000:80 ubuntu:stable /bin/bash
```
2. клонируется репозиторий 
```shell
git clone https://github.com/pmshoot/otus-pythonpro-2022-11/tree/main/homeworks/lesson07
```
3. заходим в директорию проекта 
```shell
cd hasker
```
4. собираем и запускаем проект
```shell
make prod
``` 

Тестовый сервис доступен на порту 8000 