# Use Python 3.10 as the base image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first to leverage Docker caching
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . /app/

# Expose the port (matches your docker-compose.yml)
EXPOSE 8004

# Run migrations and start Daphne (ASGI server for Channels)
CMD ["sh", "-c", "python manage.py migrate && daphne -b 0.0.0.0 -p 8004 Video_Call_Service.asgi:application"]