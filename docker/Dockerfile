FROM python:3.11

WORKDIR /

COPY . /app
RUN pip install /app

ENTRYPOINT ["/app/docker/entrypoint.sh"]
