#FROM python:alpine
#COPY requirements.txt /
#RUN python -m pip install -r requirements.txt
#EXPOSE 8000
##
#ADD hasker /hasker
#WORKDIR /hasker
##RUN python manage.py migrate
#RUN python manage.py collectstatic --noinput
#CMD ["gunicorn", "-b", "0.0.0.0:8000", "core.wsgi"]
##################
FROM ubuntu:jammy
ADD . /hasker
