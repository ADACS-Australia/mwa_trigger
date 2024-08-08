# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app
WORKDIR /app

# Install git and PostgreSQL client development libraries
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y build-essential libpq-dev gcc

# Copy requirements and install dependencies
COPY requirements_dev.txt .
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements_dev.txt

# Install production dependencies
COPY webapp_tracet/requirements.txt webapp_tracet/

# Copy the additional requirements for the Django app
RUN pip3 install -r webapp_tracet/requirements.txt
# Copy requirements file and install dependencies
COPY requirements_dev.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements_dev.txt

# Copy the application code and install production dependencies
COPY webapp_tracet/requirements.txt webapp_tracet/
RUN pip install -r webapp_tracet/requirements.txt

# Run Django development server
ENV PYTHONPATH="/app"
CMD ["python3", "webapp_tracet/manage.py", "runserver", "0.0.0.0:8000"]