# Use an official Python runtime as a parent image
FROM python:3.10-slim

WORKDIR /app
# Install git
RUN apt-get update && \
apt-get install -y git && \
apt-get install -y build-essential libpq-dev gcc && \
apt-get install -y tmux && \
apt-get install -y librdkafka++1 librdkafka-dev librdkafka1 && \ 
apt-get install -y libsasl2-modules-gssapi-mit

# Install tracet dependencies
COPY requirements.txt /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY requirements_web.txt /app/
RUN pip install -r requirements_web.txt

WORKDIR /app
ADD tracet /app/tracet
ADD tests /app/tests
COPY setup.py /app/
COPY LICENSE /app/  

RUN pip install .

COPY webapp_tracet /app/webapp_tracet

ARG SYSTEM_ENV
# Set the environment variable
ENV SYSTEM_ENV=${SYSTEM_ENV}

#ADD webapp_tracet /app/webapp_tracet
WORKDIR /app/webapp_tracet
# Collect static files

# Add this command to conditionally run collectstatic
RUN if [ "$SYSTEM_ENV" = "PRODUCTION" ]; then \
      python manage.py collectstatic --noinput; \
    fi

EXPOSE 8000
CMD [ "/bin/bash" ]

