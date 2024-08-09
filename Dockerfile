# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app/webapp_tracet

COPY . /app/webapp_tracet

# Install git and PostgreSQL client development libraries
RUN apt-get update && \
apt-get install -y git && \
apt-get install -y build-essential libpq-dev gcc

# Copy requirements and install dependencies
COPY requirements_dev.txt /app/webapp_tracet/
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements_dev.txt
RUN pip3 install .

# Install production dependencies
COPY webapp_tracet/requirements.txt webapp_tracet/

# Copy the additional requirements for the Django app
RUN pip3 install -r webapp_tracet/requirements.txt

WORKDIR /app/webapp_tracet

# Set the PYTHONPATH environment variable
ENV PYTHONPATH="/app:/app/webapp_tracet"

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"] 