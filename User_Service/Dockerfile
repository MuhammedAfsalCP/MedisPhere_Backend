# Use Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8003

# Set environment variable for Django settings
ENV DJANGO_SETTINGS_MODULE=User_Service.settings

# Start both Django server and consumer.py
CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:8003"]

