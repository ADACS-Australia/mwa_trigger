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

# Install tracet dependencies
COPY requirements.txt /app/

RUN python -m venv .venv
RUN . .venv/bin/activate
RUN pip install -r requirements.txt

ARG SYSTEM_ENV
# Set the environment variable
ENV SYSTEM_ENV=${SYSTEM_ENV}

WORKDIR /app

COPY test_api /app/test_api
COPY test_trigservices /app/test_trigservices

# Collect static files
# Add this command to conditionally run collectstatic
# RUN if [ "$SYSTEM_ENV" = "PRODUCTION" ]; then \
#       python manage.py collectstatic --noinput; \
#     fi

EXPOSE 8000
CMD [ "/bin/bash" ]