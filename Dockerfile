FROM python:3.12-slim-bookworm
RUN mkdir -p /opt/resource/
COPY requirements.txt requirements.txt

RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt --no-deps --no-cache-dir

WORKDIR /opt/resource/
COPY concourse.py ./concourse.py
RUN python3 -m concoursetools . -r concourse.py

ENTRYPOINT ["python3"]
