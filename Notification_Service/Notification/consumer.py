import os
import pika
import json
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def callback(ch, method, properties, body):
    try:
        message = json.loads(body.decode())
        # Align field names with tasks.py
        doctor_email = message.get('doctor_email')
        patient_email = message.get('patient_email')
        date = message.get('date')
        slot = message.get('slot')
        amount = message.get('amount')
        doctor_name = message.get('doctor_name')

        if not all([doctor_email, patient_email, date, slot, doctor_name]):
            raise ValueError("Missing required fields in message")

        logger.info(f"Received message: doctor_email={doctor_email}, patient_email={patient_email}, date={date}")
        # Placeholder for notification creation (without Django)
        response = {
            "status": "processed",
            "message": f"Appointment with Dr. {doctor_name} on {date} in slot {slot}"
        }

        # Send response only if reply_to is provided
        if properties.reply_to and properties.correlation_id:
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                body=json.dumps(response).encode(),
                properties=pika.BasicProperties(correlation_id=properties.correlation_id)
            )
            logger.info(f"Response sent to {properties.reply_to} with correlation_id {properties.correlation_id}")
        else:
            logger.info("No reply_to queue specified, skipping response")

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except ValueError as e:
        logger.error(f"Message validation failed: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # Requeue for transient errors

def start_consumer():
    retry_delay = 5
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            channel = connection.channel()
            channel.queue_declare(queue='booking_notifications', durable=True)
            channel.basic_consume(queue='booking_notifications', on_message_callback=callback)
            logger.info("Starting consumer... Press CTRL+C to stop.")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed, retrying in {retry_delay} seconds: {str(e)}")
            time.sleep(retry_delay)
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            if 'channel' in locals():
                channel.stop_consuming()
            if 'connection' in locals():
                connection.close()
            break
        except Exception as e:
            logger.error(f"Unexpected error, retrying in {retry_delay} seconds: {str(e)}")
            time.sleep(retry_delay)
        finally:
            if 'connection' in locals() and not connection.is_closed:
                connection.close()

if __name__ == "__main__":
    start_consumer()