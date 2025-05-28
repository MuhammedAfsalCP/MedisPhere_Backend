# Use Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8005

# Run the Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8005"]