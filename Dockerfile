# Use an official Python runtime as a parent image
FROM python:3.10-slim

WORKDIR /app
# Install git
# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    gcc \
    tmux \
    librdkafka++1 \
    librdkafka-dev \
    librdkafka1 \
    libsasl2-modules-gssapi-mit && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

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

