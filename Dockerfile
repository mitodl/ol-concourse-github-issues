FROM python:3.12-slim-bookworm@sha256:541d45d3d675fb8197f534525a671e2f8d66c882b89491f9dda271f4f94dcd06
RUN mkdir -p /opt/resource/
COPY requirements.txt requirements.txt

RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt --no-deps --no-cache-dir

WORKDIR /opt/resource/
COPY concourse.py ./concourse.py
RUN python3 -m concoursetools . -r concourse.py

ENTRYPOINT ["python3"]
