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

# Copy the init script into the container
COPY init.sh /init.sh
# Make the script executable
RUN chmod +x /init.sh
# Set the entry point to run the init script, which applies iptables rules and then runs the main CMD
ENTRYPOINT ["/init.sh"]

# Install tracet dependencies
COPY requirements_web1.txt /app/

# RUN python -m venv .venv
RUN pip install -r requirements_web1.txt

WORKDIR /app/proposal_package
ADD proposal_package /app/proposal_package 
# RUN . /app/.venv/bin/activate && pip install .
RUN pip install .

ARG SYSTEM_ENV
# Set the environment variable
ENV SYSTEM_ENV=${SYSTEM_ENV}

WORKDIR /app

COPY prop_api /app/prop_api
COPY propsettings_app /app/propsettings_app

WORKDIR /app
# Collect static files
# Add this command to conditionally run collectstatic
# RUN if [ "$SYSTEM_ENV" = "PRODUCTION" ]; then \
#       python manage.py collectstatic --noinput; \
#     fi

EXPOSE 8000
CMD [ "/bin/bash" ]