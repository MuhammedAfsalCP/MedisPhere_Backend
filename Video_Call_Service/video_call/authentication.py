import logging
import json
import pika
import uuid
import time
from queue import Queue, Empty
from types import SimpleNamespace
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone

logger = logging.getLogger('django')

class CustomJWTAuthentication(JWTAuthentication):
    def __init__(self):
        super().__init__()
        self.auth_header_types = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_HEADER_TYPES', ('Bearer',))

    def get_header(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", b"")
        if isinstance(auth, bytes):
            auth = auth.decode("utf-8")
        return auth

    def authenticate(self, request):
        logger.info("Starting token authentication")
        auth_header = self.get_header(request)
        logger.info(f"Decoded header type: {type(auth_header)}, value: {auth_header}")
        if not auth_header:
            logger.warning("No Authorization header provided in request")
            return None

        logger.info(f"Authorization header received: {auth_header}")
        try:
            auth_parts = auth_header.split()
            if len(auth_parts) != 2:
                logger.warning("Invalid Authorization header format: Expected 'Bearer <token>'")
                raise AuthenticationFailed("Invalid Authorization header format: Expected 'Bearer <token>'")
            token_type, token = auth_parts
            if not token_type or not token:
                logger.warning("Missing token type or token in Authorization header")
                raise AuthenticationFailed("Missing token type or token")

            if token_type.lower() not in (t.lower() for t in self.auth_header_types):
                logger.warning(f"Invalid token type: {token_type}, expected one of {self.auth_header_types}")
                raise AuthenticationFailed(f"Invalid token type, expected one of {self.auth_header_types}")

            logger.info(f"Validating token: {token[:20]}...")
            validated_token = self.get_validated_token(token)
            logger.info(f"Token validated successfully: {validated_token.payload}")
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationFailed(f"Authentication failed: {str(e)}")

        user = self.get_user(validated_token)
        return (user, validated_token)

    def get_user(self, validated_token):
        user_id = validated_token.get("user_id")

        if not user_id:
            logger.error("Invalid token: No user_id found")
            raise AuthenticationFailed("Invalid token: Missing user_id")

        logger.info(f"Requesting user data for ID: {user_id} via RabbitMQ")
        user_data = self.request_user_from_service(user_id)

        if not user_data or "error" in user_data:
            logger.error(f"User not found for ID: {user_id}, response: {user_data}")
            raise AuthenticationFailed(f"User not found: {user_data.get('error', 'Unknown error')}")

        logger.info(f"Successfully retrieved user data: {user_data}")
        return SimpleNamespace(**user_data, is_authenticated=True)

    def request_user_from_service(self, user_id):
        correlation_id = str(uuid.uuid4())
        response_queue = Queue(maxsize=1)

        def callback(ch, method, properties, body):
            if properties.correlation_id == correlation_id:
                logger.info(f"Received response in callback for correlation_id: {correlation_id}")
                response_queue.put(json.loads(body))
                ch.stop_consuming()

        retry_count = 0
        connection = None
        channel = None
        try:
            while retry_count < 3:
                try:
                    connection = pika.BlockingConnection(
                        pika.ConnectionParameters(
                            host=settings.RABBITMQ_HOST,
                            heartbeat=30,
                            blocked_connection_timeout=300
                        )
                    )
                    channel = connection.channel()

                    channel.queue_declare(queue="get_user", durable=True)

                    result = channel.queue_declare(queue="", exclusive=True)
                    response_queue_name = result.method.queue
                    logger.info(f"Created reply_to queue: {response_queue_name}")

                    channel.basic_consume(
                        queue=response_queue_name,
                        on_message_callback=callback,
                        auto_ack=True
                    )
                    logger.info(f"Started consuming on reply_to queue: {response_queue_name}")

                    message = json.dumps({"user_id": user_id})
                    channel.basic_publish(
                        exchange="",
                        routing_key="get_user",
                        body=message,
                        properties=pika.BasicProperties(
                            reply_to=response_queue_name,
                            correlation_id=correlation_id,
                            delivery_mode=2
                        )
                    )
                    logger.info(f"Sent user request for ID: {user_id} with correlation_id: {correlation_id}")

                    start_time = time.time()
                    timeout = 10
                    while time.time() - start_time < timeout:
                        try:
                            response = response_queue.get_nowait()
                            logger.info(f"Received response for user {user_id}: {response}")
                            return response
                        except Empty:
                            connection.process_data_events(time_limit=1)
                            continue

                    logger.error("Timeout waiting for RabbitMQ response after 10 seconds")
                    return {"error": "Request timed out after 10 seconds"}

                except pika.exceptions.AMQPConnectionError as e:
                    logger.error(f"RabbitMQ connection error on attempt {retry_count + 1}/3: {str(e)}")
                    retry_count += 1
                    if retry_count < 3:
                        logger.info(f"Retrying in 1 second...")
                        time.sleep(1)
                    else:
                        logger.error("Max retries reached for RabbitMQ connection")
                        return {"error": "RabbitMQ unavailable after retries"}
                except Exception as e:
                    logger.error(f"Error in RabbitMQ request: {str(e)}")
                    return {"error": str(e)}
        finally:
            if channel:
                channel.close()
            if connection:
                connection.close()

        return {"error": "Failed to connect to RabbitMQ after retries"}