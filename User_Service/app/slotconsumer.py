# import pika
# import json
# import time
# import logging
# import os
# import django
# import sys


# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# django.setup()

# #  Import Models
# from app.models import UserProfile, DoctorAvailability
# from django.db import transaction

# #  Configure Logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[
#         logging.FileHandler("consumer.log"),  # Save logs
#         logging.StreamHandler()  # Print logs
#     ]
# )
# logger = logging.getLogger(__name__)
# logger.info("hlo")
# #  RabbitMQ Connection
# def connect_to_rabbitmq():
#     retries = 15
#     for i in range(retries):
#         try:
#             connection = pika.BlockingConnection(
#                 pika.ConnectionParameters(
#                     host="rabbitmq",
#                     heartbeat=600,
#                     blocked_connection_timeout=300,
#                 )
#             )
#             logging.info(" Connected to RabbitMQ successfully.")
#             return connection
#         except pika.exceptions.AMQPConnectionError:
#             logging.warning(f"Retry {i+1}/{retries} - Waiting for RabbitMQ...")
#             time.sleep(5)
#     logging.error(" Failed to connect to RabbitMQ.")
#     raise Exception("Failed to connect to RabbitMQ.")

# #  Doctor Slot Creation
# def doctor_slot_creation(data):
#     doctor_firstname = data.get("doctor_name")
#     date = data.get("date")
#     slot = data.get("slot")

#     try:
#         doctor = UserProfile.objects.get(first_name=doctor_firstname, is_doctor=True)
#         logger.info(doctor)
#         with transaction.atomic():
#             #  Prevent duplicate slot creation
#             existing_slot = DoctorAvailability.objects.filter(doctor=doctor, date=date, slot=slot).first()
#             if existing_slot:
#                 logging.warning(f" Slot already exists for Dr. {doctor_firstname} on {date} at {slot}.")
#                 return {"status": "Slot Already Exists"}

#             #  Create Slot
#             DoctorAvailability.objects.create(doctor=doctor, date=date, slot=slot)
#             logging.info(f" Slot created for Dr. {doctor_firstname} on {date} at {slot}.")
#             return {"status": "Slot Created", "date":{date},"slot":{slot}}

#     except UserProfile.DoesNotExist:
#         logging.error(f"Doctor '{doctor_firstname}' not found.")
#         return {"error": "Doctor not found"}

#     except Exception as e:
#         logging.error(f"Database error: {e}")
#         return {"error": "Database connection failed"}


# def callback(ch, method, properties, body):
#     """Handles incoming RabbitMQ messages"""
#     try:
#         raw_message = body.decode("utf-8").strip()  
#         logging.info(f"📥 Raw message received: {raw_message}")

       
#         try:
#             data = json.loads(raw_message)
#         except json.JSONDecodeError as e:
#             logging.error(f" JSON Decode Error: {e}. Raw message: {raw_message}")
#             response = {"error": "Invalid JSON format"}
#         else:
#             logging.info(f"Parsed JSON: {data}")
#             response = doctor_slot_creation(data)

#     except Exception as e:
#         logging.error(f" Error processing message: {e}")
#         response = {"error": str(e)}

#     # Send Response Back
#     ch.basic_publish(
#         exchange="",
#         routing_key=properties.reply_to,
#         properties=pika.BasicProperties(correlation_id=properties.correlation_id),
#         body=json.dumps(response),  # Ensure valid JSON response
#     )

#     #  Acknowledge the message
#     ch.basic_ack(delivery_tag=method.delivery_tag)
#     logging.info(f"📤 Sent response: {response}")

# def start_consumer():
#     """Starts RabbitMQ consumer and ensures connection recovery"""
#     while True:
#         try:
#             logging.info("Connecting to RabbitMQ...")
#             connection = connect_to_rabbitmq()
#             channel = connection.channel()
#             channel.queue_declare(queue="doctor_slot_creation", durable=True)
#             channel.basic_qos(prefetch_count=1)
#             channel.basic_consume(queue="doctor_slot_creation", on_message_callback=callback)

#             logging.info(" [✔] Waiting for messages from Appointment Service...")
#             channel.start_consuming()

#         except pika.exceptions.AMQPConnectionError as e:
#             logging.error(f"RabbitMQ connection lost: {e}. Reconnecting in 5 seconds...")
#             time.sleep(5)  # Wait and retry if RabbitMQ crashes

#         except Exception as e:
#             logging.error(f"Consumer error: {e}. Restarting in 5 seconds...")
#             time.sleep(5)

# if __name__ == "__main__":
#     logging.info("Starting consumer... Waiting 5 seconds to ensure RabbitMQ is ready.")
#     time.sleep(5)  # Ensures RabbitMQ is ready before starting
#     start_consumer()



import pika
import json
import time
import logging
import os
import django
import sys


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "User_Service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

#  Import Models
from app.models import UserProfile, DoctorAvailability
from django.db import transaction

#  Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("consumer.log"),  # Save logs
        logging.StreamHandler()  # Print logs
    ]
)
logger = logging.getLogger(__name__)
logger.info("hlo")


#  RabbitMQ Connection
def connect_to_rabbitmq():
    retries = 15
    for i in range(retries):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )
            logger.info(" Connected to RabbitMQ successfully.")
            return connection
        except pika.exceptions.AMQPConnectionError:
            logger.warning(f"Retry {i+1}/{retries} - Waiting for RabbitMQ...")
            time.sleep(5)
    logger.error(" Failed to connect to RabbitMQ.")
    raise Exception("Failed to connect to RabbitMQ.")


#  Doctor Slot Creation
def doctor_slot_creation(data):
    doctor_firstname = data.get("doctor_name")
    date = data.get("date")
    slot = data.get("slot")

    try:
        doctor = UserProfile.objects.get(first_name=doctor_firstname, is_doctor=True)
        logger.info(doctor)
        with transaction.atomic():
            #  Prevent duplicate slot creation
            existing_slot = DoctorAvailability.objects.filter(doctor=doctor, date=date, slot=slot).first()
            if existing_slot:
                logger.warning(f" Slot already exists for Dr. {doctor_firstname} on {date} at {slot}.")
                return {"status": "Slot Already Exists"}

            #  Create Slot
            DoctorAvailability.objects.create(doctor=doctor, date=date, slot=slot)
            logger.info(f" Slot created for Dr. {doctor_firstname} on {date} at {slot}.")
            return {"status": "Slot Created", "date": date, "slot": slot}

    except UserProfile.DoesNotExist:
        logger.error(f"Doctor '{doctor_firstname}' not found.")
        return {"error": "Doctor not found"}

    except Exception as e:
        logger.error(f"Database error: {e}")
        return {"error": "Database connection failed"}


def callback(ch, method, properties, body):
    """Handles incoming RabbitMQ messages"""
    try:
        raw_message = body.decode("utf-8").strip()
        logger.info(f"📥 Raw message received: {raw_message}")

        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError as e:
            logger.error(f" JSON Decode Error: {e}. Raw message: {raw_message}")
            response = {"error": "Invalid JSON format"}
        else:
            logger.info(f"Parsed JSON: {data}")
            response = doctor_slot_creation(data)

    except Exception as e:
        logger.error(f" Error processing message: {e}")
        response = {"error": str(e)}

    # Send Response Back
    ch.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        body=json.dumps(response),  # Ensure valid JSON response
    )

    #  Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)
    logger.info(f"📤 Sent response: {response}")


def start_consumer():
    """Starts RabbitMQ consumer and ensures connection recovery"""
    while True:
        connection = None  # Initialize connection variable
        try:
            logger.info("Connecting to RabbitMQ...")
            connection = connect_to_rabbitmq()
            channel = connection.channel()
            channel.queue_declare(queue='doctor_slot_creation', durable=False)

  # ✅ Fixed durability issue
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="doctor_slot_creation", on_message_callback=callback)

            logger.info(" [✔] Waiting for messages from Appointment Service...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection lost: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)

        except Exception as e:
            logger.error(f"Consumer error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

        finally:
            if connection and not connection.is_closed:
                logger.info("Closing RabbitMQ connection.")
                connection.close()


if __name__ == "__main__":
    logger.info("Starting consumer... Waiting 5 seconds to ensure RabbitMQ is ready.")
    time.sleep(5)  # Ensures RabbitMQ is ready before starting
    start_consumer()
