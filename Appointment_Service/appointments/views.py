from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pika
import json
import uuid
import time
import logging
from rest_framework.permissions import AllowAny, IsAdminUser
from django.conf import settings
# Setup logging
logger = logging.getLogger(__name__)
from .permissions import IsDoctor, IsAdmin, IsStaff, IsPatient

class BookingAppointmentAPIView(APIView):
    """API to create an appointment by checking doctor availability via RabbitMQ"""
    permission_classes=[IsPatient]
    def post(self, request):
        data = request.data
        doctor_email = data.get("doctor_email")
        date = data.get("date")
        slot = data.get("slot")
        patient_email = data.get("patient_email")
        correlation_id = str(uuid.uuid4())
        doctor_response = None

        try:
            # Setup RabbitMQ connection
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            channel = connection.channel()

            # Declare the queue
            channel.queue_declare(queue="check_doctor_availability")

            # Create a temporary response queue
            response_queue = channel.queue_declare(queue="", exclusive=True)
            response_queue_name = response_queue.method.queue

            # Set prefetch count to 1 (Fair dispatch)
            channel.basic_qos(prefetch_count=1)

            def on_response(ch, method, properties, body):
                """Callback function to handle RabbitMQ response"""
                nonlocal doctor_response
                try:
                    if properties.correlation_id == correlation_id:
                        doctor_response = json.loads(body)
                        logger.info(f"Received response: {doctor_response}")
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from RabbitMQ")

            # Start consuming response queue asynchronously
            channel.basic_consume(
                queue=response_queue_name,
                on_message_callback=on_response,
                auto_ack=True,
            )

            # Send request to RabbitMQ queue
            request_data = json.dumps(
                {
                    "doctor_email": doctor_email,
                    "date": date,
                    "slot": slot,
                    "patient_email": patient_email,
                }
            )
            channel.basic_publish(
                exchange="",
                routing_key="check_doctor_availability",
                properties=pika.BasicProperties(
                    reply_to=response_queue_name,
                    correlation_id=correlation_id,
                ),
                body=request_data,
            )
            logger.info(f"Sent request: {request_data}")

            # Wait for response (Max 5 seconds to prevent infinite loop)
            timeout = time.time() + 5  # 5-second timeout
            while doctor_response is None and time.time() < timeout:
                try:
                    connection.process_data_events(
                        time_limit=1
                    )  # Allow other tasks to run
                except pika.exceptions.AMQPConnectionError:
                    logger.error("RabbitMQ connection lost while waiting for response")
                    return Response(
                        {"error": "RabbitMQ connection lost"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ service unavailable")
            return Response(
                {"error": "RabbitMQ service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Ensure RabbitMQ connection is closed properly
            if "connection" in locals() and connection.is_open:
                connection.close()

        # If no response, return an error
        if doctor_response is None:
            logger.warning("No response from BookingAppointment Service")
            return Response(
                {"error": "No response from BookingAppointment service"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        # Check the doctor's availability
        if doctor_response.get("error"):
            return Response(
                {"error": doctor_response["error"]}, status=status.HTTP_404_NOT_FOUND
            )

        if doctor_response["available"] == False:
            return Response(
                {
                    "message": "Appointment confirmed",
                    "doctor_name": doctor_response["doctor_name"],
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "message": "Doctor is not available",
                    "doctor_name": doctor_response["doctor_name"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
    def get(self, request):
        correlation_id = str(uuid.uuid4())
        response = None

        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    heartbeat=30,
                    blocked_connection_timeout=300
                )
            )
            channel = connection.channel()

            channel.queue_declare(queue="get_doctors", durable=True)

            response_queue = channel.queue_declare(queue="", exclusive=True)
            response_queue_name = response_queue.method.queue
            logger.info(f"Created reply_to queue: {response_queue_name}")

            channel.basic_qos(prefetch_count=1)

            def on_response(ch, method, properties, body):
                nonlocal response
                try:
                    if properties.correlation_id == correlation_id:
                        response = json.loads(body)
                        logger.info(f"Received response: {response}")
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from RabbitMQ")

            channel.basic_consume(
                queue=response_queue_name,
                on_message_callback=on_response,
                auto_ack=True,
            )
            logger.info(f"Started consuming on reply_to queue: {response_queue_name}")

            # Send request with an empty body (or include user_id if needed)
            channel.basic_publish(
                exchange="",
                routing_key="get_doctors",
                body="{}",  # Empty JSON object as body
                properties=pika.BasicProperties(
                    reply_to=response_queue_name,
                    correlation_id=correlation_id,
                ),
            )
            logger.info(f"Sent doctor request with correlation_id: {correlation_id}")

            # Wait for response with a 10-second timeout
            start_time = time.time()
            timeout = 10
            while response is None and time.time() - start_time < timeout:
                connection.process_data_events(time_limit=1)

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection error: {str(e)}")
            return Response(
                {"error": "RabbitMQ connection lost"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            if 'channel' in locals():
                channel.close()
            if 'connection' in locals() and connection.is_open:
                connection.close()

        if response is None:
            logger.warning("No response from User Service")
            return Response(
                {"error": "No response from User Service"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        if response.get("error"):
            return Response(
                {"error": response["error"]}, status=status.HTTP_404_NOT_FOUND
            )
        else:
            return Response(
                {"doctors": response.get("doctors", [])},
                status=status.HTTP_200_OK,  # Changed to 200 for successful retrieval
            )


class DoctorSlotCreating(APIView):
    """API to create an appointment by checking doctor availability via RabbitMQ"""
    permission_classes=[IsDoctor]
    def post(self, request):
        data = request.data
        doctor_email = data.get("doctor_email")
        date = data.get("date")
        slot = data.get("slot")

        correlation_id = str(uuid.uuid4())
        doctor_response = None

        try:
            # Setup RabbitMQ connection
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            channel = connection.channel()

            # Declare the queue
            channel.queue_declare(queue="doctor_slot_creation")

            # Create a temporary response queue
            response_queue = channel.queue_declare(queue="", exclusive=True)
            response_queue_name = response_queue.method.queue

            # Set prefetch count to 1 (Fair dispatch)
            channel.basic_qos(prefetch_count=1)

            def on_response(ch, method, properties, body):
                """Callback function to handle RabbitMQ response"""
                nonlocal doctor_response
                try:
                    if properties.correlation_id == correlation_id:
                        doctor_response = json.loads(body)
                        logger.info(f"Received response: {doctor_response}")
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from RabbitMQ")

            # Start consuming response queue asynchronously
            channel.basic_consume(
                queue=response_queue_name,
                on_message_callback=on_response,
                auto_ack=True,
            )

            # Send request to RabbitMQ queue
            request_data = json.dumps(
                {
                    "doctor_email": doctor_email,
                    "date": date,
                    "slot": slot,
                }
            )
            channel.basic_publish(
                exchange="",
                routing_key="doctor_slot_creation",
                properties=pika.BasicProperties(
                    reply_to=response_queue_name,
                    correlation_id=correlation_id,
                ),
                body=request_data,
            )
            logger.info(f"Sent request: {request_data}")

            # Wait for response (Max 5 seconds to prevent infinite loop)
            timeout = time.time() + 5  # 5-second timeout
            while doctor_response is None and time.time() < timeout:
                try:
                    connection.process_data_events(
                        time_limit=1
                    )  # Allow other tasks to run
                except pika.exceptions.AMQPConnectionError:
                    logger.error("RabbitMQ connection lost while waiting for response")
                    return Response(
                        {"error": "RabbitMQ connection lost"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ service unavailable")
            return Response(
                {"error": "RabbitMQ service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Ensure RabbitMQ connection is closed properly
            if "connection" in locals() and connection.is_open:
                connection.close()

        # If no response, return an error
        if doctor_response is None:
            logger.warning("No response from doctor availability service")
            return Response(
                {"error": "No response from doctor availability service"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        # Check the doctor's availability
        if doctor_response.get("error"):
            return Response(
                {"error": doctor_response["error"]}, status=status.HTTP_404_NOT_FOUND
            )

        if doctor_response["status"] == "Slot Created":
            return Response(
                {"message": f" Slot created on {date} at {slot}."},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"message": "Aldredy created"}, status=status.HTTP_400_BAD_REQUEST
            )
