# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app/webapp_tracet

# Copy the current directory contents into the container at /app
COPY . /app/webapp_tracet

# Install git and PostgreSQL client development libraries
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y build-essential libpq-dev gcc netcat-openbsd

# Install any needed packages specified in requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN pip3 install .

# Install uwsgi
RUN pip3 install uwsgi

# Copy the additional requirements for the Django app
RUN pip3 install -r webapp_tracet/requirements.txt

# Copy the entrypoint script into the Docker image
COPY entrypoint.sh /entrypoint.sh

# Make sure the script is executable
RUN chmod +x /entrypoint.sh

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV NAME World

# Run uWSGI server
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uwsgi", "--ini", "/app/webapp_tracet/webapp_tracet_uwsgi.ini"]