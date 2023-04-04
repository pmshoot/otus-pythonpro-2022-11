prod: prepare_sys prepare_db prepare_wsgi prepare_nginx prepare_django

prepare_sys:
	apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3 python3-pip nginx postgresql sudo
	pip --no-input install -r /hasker/requirements.txt


prepare_wsgi:
	gunicorn -D --chdir /hasker/hasker -e DJANGO_SETTINGS_MODULE=core.settings.prod -b 127.0.0.1:8000 core.wsgi

prepare_db:
	/etc/init.d/postgresql start
	sudo -u postgres createuser --createdb dba
	sudo -u postgres createdb --owner dba hasker
	sudo -u postgres psql -c "ALTER USER dba WITH ENCRYPTED PASSWORD 'dba';"

prepare_nginx:
	cp -f /hasker/accessory/nginx/default /etc/nginx/sites-available/
	/etc/init.d/nginx start

prepare_django:
	#cd /hasker/hasker
	DJANGO_SETTINGS_MODULE=core.settings.prod python3 /hasker/hasker/manage.py migrate
	DJANGO_SETTINGS_MODULE=core.settings.prod python3 /hasker/hasker/manage.py collectstatic --noinput

tests:
	#cd /hasker/hasker
	DJANGO_SETTINGS_MODULE=core.settings.prod python3 /hasker/hasker/manage.py tests

.PHONY: prepare_sys prepare_wsgi prepare_db prepare_nginx prepare_django tests prod

