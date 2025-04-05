from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pika
import json
import uuid
import time
import logging

from .permissions import IsAdmin, IsDoctor, IsPatient


# Setup logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv()


class WalletEditing(APIView):
    """API to create an appointment by checking doctor availability via RabbitMQ"""

    permission_classes = [IsDoctor]

    def post(self, request):
        data = request.data
        user = request.user
        amount = data.get("amount")
        room_id = data.get("room_id")
        doctor_id = user.id

        if not all([id]):
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )
        correlation_id = str(uuid.uuid4())
        doctor_response = None

        try:
            # Setup RabbitMQ connection
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            channel = connection.channel()

            # Declare the queue
            channel.queue_declare(queue="walletadd", durable=True)

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
                {"amount": amount, "doctor_id": doctor_id, "room_id": room_id}
            )
            channel.basic_publish(
                exchange="",
                routing_key="walletadd",
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

        return Response(
            {"message": doctor_response.get("message", "Appointment rescheduled")},
            status=status.HTTP_201_CREATED,
        )
