FROM python:3.10-slim

WORKDIR /app
# Install git
RUN apt-get update && \
apt-get install -y git
# apt-get install -y build-essential libpq-dev gcc && \
# apt-get install -y tmux && \
# apt-get install -y librdkafka++1 librdkafka-dev librdkafka1 && \ 
# apt-get install -y libsasl2-modules-gssapi-mit

# Install tracet dependencies
COPY requirements_propapi.txt /app/

RUN python -m venv .venv
RUN . .venv/bin/activate
RUN pip install -r requirements_propapi.txt

WORKDIR /app/proposal_package
ADD proposal_package /app/proposal_package 
RUN pip install .

ARG SYSTEM_ENV
# Set the environment variable
ENV SYSTEM_ENV=${SYSTEM_ENV}

WORKDIR /app

COPY prop_api /app/prop_api
COPY propsettings_app /app/propsettings_app

# Collect static files
# Add this command to conditionally run collectstatic
# RUN if [ "$SYSTEM_ENV" = "PRODUCTION" ]; then \
#       python manage.py collectstatic --noinput; \
#     fi

EXPOSE 8000
CMD [ "/bin/bash" ]