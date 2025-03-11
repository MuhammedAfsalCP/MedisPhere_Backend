import pika
import json
import uuid

# Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# Declare a queue for appointment requests
channel.queue_declare(queue="appointment_requests")

# Create a temporary queue for receiving responses
response_queue = channel.queue_declare(queue="", exclusive=True)
response_queue_name = response_queue.method.queue

doctor_response = None


def on_response(ch, method, properties, body):
    """Handles responses from User Service"""
    global doctor_response
    doctor_response = json.loads(body)


def check_doctor_availability(doctor_id, date, slot):
    """Sends a request to User Service to check doctor availability"""
    global doctor_response
    doctor_response = None  # Reset response

    correlation_id = str(uuid.uuid4())

    request_data = {"doctor_id": doctor_id, "date": date, "slot": slot}
    request_json = json.dumps(request_data)

    channel.basic_publish(
        exchange="",
        routing_key="check_doctor_availability",
        properties=pika.BasicProperties(
            reply_to=response_queue_name, correlation_id=correlation_id
        ),
        body=request_json,
    )

    while doctor_response is None:
        connection.process_data_events()

    return doctor_response


# Function to process appointment requests
def process_appointment_request(ch, method, properties, body):
    data = body.decode().split(",")
    patient_id, doctor_id, date, slot = data

    print(f"Checking availability for Doctor {doctor_id} on {date} at {slot}")

    # Get doctor availability from User Service
    doctor_availability = check_doctor_availability(doctor_id, date, slot)

    if "error" in doctor_availability:
        print("Doctor not found!")
        return

    doctor_name = doctor_availability["doctor_name"]

    if doctor_availability["available"]:
        print(f"Doctor {doctor_name} is available. Confirming appointment...")
        # Here, you can update appointment records in the database
    else:
        print(f"Doctor {doctor_name} is NOT available. Rejecting appointment.")


# Start consuming appointment requests
channel.basic_consume(
    queue="appointment_requests",
    on_message_callback=process_appointment_request,
    auto_ack=True,
)
channel.basic_consume(
    queue=response_queue_name, on_message_callback=on_response, auto_ack=True
)

print("Appointment Service is waiting for requests...")
channel.start_consuming()
