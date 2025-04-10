#!/bin/bash
set -e

until python -c "import socket; socket.create_connection(('db', 5432))" 2>/dev/null; do
  echo "Waiting for database..."
  sleep 2
done

until python -c "import socket; socket.create_connection(('rabbitmq', 5672))" 2>/dev/null; do
  echo "Waiting for RabbitMQ..."
  sleep 2
done

until python -c "import socket; socket.create_connection(('redis', 6379))" 2>/dev/null; do
  echo "Waiting for Redis..."
  sleep 2
done

python manage.py migrate --noinput

exec "$@"