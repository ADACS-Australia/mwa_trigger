# Use an official Python runtime as a parent image
FROM python:3.10-slim

WORKDIR /app
# Install git
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y iptables && \
    apt-get install -y curl && \
    apt-get install -y dnsutils && \
    apt-get install -y build-essential libpq-dev gcc && \
    apt-get install -y tmux && \
    apt-get install -y librdkafka++1 librdkafka-dev librdkafka1 && \ 
    apt-get install -y libsasl2-modules-gssapi-mit

# Update alternatives to make iptables-legacy the default
RUN update-alternatives --set iptables /usr/sbin/iptables-legacy \
    && update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy


# create the appropriate directories
# ENV HOME=/app
# ENV APP_HOME=/app/webapp_tracet

# Install tracet dependencies
COPY tracet_package/requirements.txt /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY requirements_web.txt /app/
RUN pip install -r requirements_web.txt

WORKDIR /app/tracet_package
ADD tracet_package /app/tracet_package 
RUN pip install .

WORKDIR /app
COPY webapp_tracet /app/webapp_tracet
COPY trigger_app /app/trigger_app


ARG SYSTEM_ENV
# Set the environment variable
ENV SYSTEM_ENV=${SYSTEM_ENV}

#ADD webapp_tracet /app/webapp_tracet
WORKDIR /app
# Collect static files

# Add this command to conditionally run collectstatic
RUN if [ "$SYSTEM_ENV" = "PRODUCTION" ]; then \
    python manage.py collectstatic --noinput; \
    fi

EXPOSE 8000
CMD [ "/bin/bash" ]

