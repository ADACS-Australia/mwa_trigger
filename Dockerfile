# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

COPY . /app

# Install git
RUN apt-get update && \
apt-get install -y git && \
apt-get install -y build-essential libpq-dev gcc

# Install tracet dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install .

# Install web application dependencies
RUN pip install -r webapp_tracet/requirements.txt

WORKDIR /app/webapp_tracet
CMD [ "/bin/bash" ]