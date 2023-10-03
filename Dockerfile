FROM python:3.11-bookworm

WORKDIR /app
ADD . /app

RUN pip install .
