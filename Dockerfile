FROM python:3.11-slim-bookworm
LABEL mitodl/ol-concourse-github-issues
RUN mkdir -p /opt/resource/ && useradd -b /opt/resource/ -s /bin/false -M app && chown -R app:app /opt/resource
COPY requirements.txt requirements.txt

RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt --no-deps --no-cache-dir

USER app
WORKDIR /opt/resource/
COPY concourse.py ./concourse.py
RUN python3 -m concoursetools . -r concourse.py

ENTRYPOINT ["python3"]
