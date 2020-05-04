FROM amsterdam/python:3.8-buster as app

ENV PYTHONUNBUFFERED 1
ENV CONSUL_HOST=${CONSUL_HOST:-notset}
ENV CONSUL_PORT=${CONSUL_PORT:-8500}
ENV DATAPUNT_API_URL=${DATAPUNT_API_URL:-https://api.data.amsterdam.nl/}

ARG https_proxy=http://10.240.2.1:8080/
ENV https_proxy=$https_proxy

WORKDIR /app_install
ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

ADD deploy /deploy

WORKDIR /src
ADD src .

ARG SECRET_KEY=collectstatic 
RUN python manage.py collectstatic --no-input

USER datapunt

CMD ["/deploy/docker-run.sh"]

# devserver
FROM app as dev

USER root
WORKDIR /app_install
ADD requirements_dev.txt requirements_dev.txt
RUN pip install -r requirements_dev.txt
RUN chmod -R a+r /app_install

WORKDIR /src
USER datapunt

# Any process that requires to write in the home dir
# we write to /tmp since we have no home dir
ENV HOME /tmp

CMD ["python manage.py runserver 0.0.0.0"]

# tests
FROM dev as tests

USER datapunt

ENV COVERAGE_FILE=/tmp/.coverage

CMD ["pytest"]
