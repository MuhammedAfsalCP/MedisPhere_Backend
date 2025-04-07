# notification_service/consumer.py
import pika
import json
from datetime import datetime
from .notification import create_booking_notification

def callback(ch, method, properties, body):
    message = json.loads(body.decode())
    doctor_id = message['doctor_id']
    patient_id = message['patient_id']
    booking_time = datetime.strptime(message['booking_time'], '%Y-%m-%d %H:%M:%S')
    slot = message['slot']
    patient_email = message['patient_email']
    doctor_name = message['doctor_name']

    create_booking_notification(doctor_id, patient_id, booking_time, slot, patient_email, doctor_name)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    # Establish connection to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declare the queue (must match the queue name used in UserService)
    channel.queue_declare(queue='booking_notifications', durable=True)

    # Set up the consumer
    channel.basic_consume(queue='booking_notifications', on_message_callback=callback)

    # Start consuming messages
    print("Starting consumer... Press CTRL+C to stop.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()

if __name__ == "__main__":
    start_consumer()