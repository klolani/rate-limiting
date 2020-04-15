FROM python:3.7-alpine

ADD rate_limiting.py /

RUN pip install redis

ENTRYPOINT [ "python", "./rate_limiting.py" ]
