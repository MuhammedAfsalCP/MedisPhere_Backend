from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pika
import json
import uuid
import time
import logging
from rest_framework.permissions import AllowAny, IsAdminUser
from .permissions import IsAdmin,IsDoctor,IsPatient 
from django.conf import settings
# Setup logging
logger = logging.getLogger(__name__)

import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

class BookingAppointmentAPIView(APIView):
    """
    API to process Razorpay payments and finalize appointment booking.
    Assumes doctor availability has already been confirmed.
    """

    def post(self, request):
        """
        Handles the payment flow:
        1. Initiates payment if no payment details are provided
        2. Verifies payment and books the slot if payment details are provided
        """
        data = request.data
        doctor_email = data.get("doctor_email")
        date = data.get("date")
        slot = data.get("slot")
        amount = data.get("amount")  # Amount in INR
        razorpay_payment_id = data.get("payment_id")
        razorpay_order_id = data.get("order_id")
        razorpay_signature = data.get("signature")

        user = request.user
        patient_email = user.email

        logger.info(f"Received booking request: {data}, patient_email={patient_email}")

        # Validate required fields
        if not all([doctor_email, date, slot, amount]):
            logger.error("Missing required fields in request")
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        # If payment details are provided, verify payment and book
        if razorpay_payment_id and razorpay_order_id and razorpay_signature:
            return self.verify_payment(
                razorpay_payment_id, razorpay_order_id, razorpay_signature,
                doctor_email, patient_email, date, slot, amount
            )
        
        # Otherwise, initiate payment
        return self.initiate_payment(doctor_email, patient_email, date, slot, amount)

    def initiate_payment(self, doctor_email, patient_email, date, slot, amount):
        """
        Initiates a payment using Razorpay.
        """
        try:
            razorpay_client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
            amount_in_paise = int(float(amount) * 100)

            order_data = {
                "amount": amount_in_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "doctor_email": doctor_email,
                    "patient_email": patient_email,
                    "date": date,
                    "slot": slot,
                },
            }

            order = razorpay_client.order.create(order_data)

            logger.info(f"Payment initiated for {patient_email} - Order ID: {order['id']}")
            return Response({
                "message": "Payment initiated",
                "order_id": order["id"],
                "amount": amount,
                "currency": "INR",
                "razorpay_key": os.getenv("RAZORPAY_KEY_ID"),
            }, status=status.HTTP_201_CREATED)

        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            logger.error(f"Invalid amount format: {str(e)}")
            return Response({"error": "Invalid amount format"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Payment initiation error: {str(e)}")
            return Response({"error": "Failed to initiate payment"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_payment(self, razorpay_payment_id, razorpay_order_id, razorpay_signature, doctor_email, patient_email, date, slot, amount):
        """
        Verifies the Razorpay payment and triggers booking request.
        """
        logger.info(f"Verifying payment - Order ID: {razorpay_order_id}")
        try:
            client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })

            logger.info(f"Payment verified successfully for {patient_email} - Payment ID: {razorpay_payment_id}")
            return self.send_booking_request(doctor_email, patient_email, date, slot, amount)

        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Payment signature verification failed: {str(e)}")
            return Response({"error": "Invalid payment signature"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return Response({"error": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)

    def send_booking_request(self, doctor_email, patient_email, date, slot, amount):
        """
        Sends booking details to 'slotbooking' queue via RabbitMQ.
        """
        logger.info(f"Sending booking request for {patient_email} to slotbooking queue")
        correlation_id = str(uuid.uuid4())
        booking_response = None
        connection = None

        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq", heartbeat=600)
            )
            channel = connection.channel()
            channel.queue_declare(queue="slotbooking", durable=True)
            logger.info("RabbitMQ connection and queue declared successfully")

            response_queue = channel.queue_declare(queue="", exclusive=True, auto_delete=True)
            response_queue_name = response_queue.method.queue

            def on_response(ch, method, properties, body):
                nonlocal booking_response
                if properties.correlation_id == correlation_id:
                    try:
                        booking_response = json.loads(body.decode())
                        logger.info(f"Received booking response: {booking_response} - Correlation ID: {correlation_id}")
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON response - Correlation ID: {correlation_id}")

            channel.basic_consume(queue=response_queue_name, on_message_callback=on_response, auto_ack=True)

            request_data = json.dumps({
                "doctor_email": doctor_email,
                "patient_email": patient_email,
                "date": date,
                "slot": slot,
                "amount": amount,
            })

            channel.basic_publish(
                exchange="",
                routing_key="slotbooking",
                properties=pika.BasicProperties(
                    reply_to=response_queue_name,
                    correlation_id=correlation_id,
                    delivery_mode=2
                ),
                body=request_data.encode(),
            )
            logger.info(f"Booking request published to slotbooking queue: {request_data} - Correlation ID: {correlation_id}")

            timeout = time.time() + 5
            while booking_response is None and time.time() < timeout:
                connection.process_data_events(time_limit=1)

            if booking_response is None:
                logger.error(f"Timeout waiting for booking response - Correlation ID: {correlation_id}")
                return Response({"error": "Booking request timed out"}, status=status.HTTP_504_GATEWAY_TIMEOUT)

            if "error" in booking_response:
                logger.error(f"Booking failed: {booking_response['error']} - Correlation ID: {correlation_id}")
                return Response({"error": booking_response["error"]}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Booking successful for {patient_email} - Status: {booking_response.get('status')}")
            return Response({
                "message": "Booking request processed successfully",
                "booking_details": {
                    "doctor_email": doctor_email,
                    "patient_email": patient_email,
                    "date": date,
                    "slot": slot,
                    "amount": amount,
                    "status": booking_response.get("status", "Pending")
                }
            }, status=status.HTTP_200_OK)

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed: {str(e)} - Correlation ID: {correlation_id}")
            return Response({"error": "Booking service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Booking error: {str(e)} - Correlation ID: {correlation_id}")
            return Response({"error": "Failed to process booking request"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if connection and not connection.is_closed:
                connection.close()

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



class DoctorFetching(APIView):
    """API to create an appointment by checking doctor availability via RabbitMQ"""
    permission_classes=[IsPatient]
    def get(self, request,department):
        

        correlation_id = str(uuid.uuid4())
        doctor_response = None

        try:
            # Setup RabbitMQ connection
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            channel = connection.channel()

            # Declare the queue
            channel.queue_declare(queue="get_doctors",durable=True)

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
                    "department": department
                }
            )
            channel.basic_publish(
                exchange="",
                routing_key="get_doctors",
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
                {"doctors": doctor_response.get("doctors")},
                status=status.HTTP_201_CREATED,
            )
        
class Specificdoctorfetching(APIView):
    """API to create an appointment by checking doctor availability via RabbitMQ"""
    permission_classes=[IsPatient]
    def get(self, request,id):
        

        correlation_id = str(uuid.uuid4())
        doctor_response = None

        try:
            # Setup RabbitMQ connection
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            channel = connection.channel()

            # Declare the queue
            channel.queue_declare(queue="specific_doctor_fetching",durable=True)

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
                    "id": id
                }
            )
            channel.basic_publish(
                exchange="",
                routing_key="specific_doctor_fetching",
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
                {"doctor": doctor_response.get("doctors")},
                status=status.HTTP_201_CREATED,
            )


class Slotfetching(APIView):
    """API to create an appointment by checking doctor availability via RabbitMQ"""
    permission_classes=[IsPatient]
    def get(self, request,id,date):
        

        correlation_id = str(uuid.uuid4())
        doctor_response = None

        try:
            # Setup RabbitMQ connection
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            channel = connection.channel()

            # Declare the queue
            channel.queue_declare(queue="slot_fetching",durable=True)

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
                    "id": id,
                    "date":date
                }
            )
            channel.basic_publish(
                exchange="",
                routing_key="slot_fetching",
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
                {"slots": doctor_response.get("slots")},
                status=status.HTTP_201_CREATED,
            )
