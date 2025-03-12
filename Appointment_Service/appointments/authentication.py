import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from types import SimpleNamespace
import json
import pika
from django.conf import settings

logger = logging.getLogger("django")

class CustomJWTAuthentication(JWTAuthentication):
    def get_header(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        logger.info(f"Authorization header: {auth}")
        return auth

    def get_user(self, validated_token):
        logger.info(f"Validated token: {validated_token}")
        user_id = validated_token.get("user_id")
        if not user_id:
            logger.error("Invalid token: No user_id found")
            raise AuthenticationFailed("Invalid token: Missing user_id")

        logger.info(f"Requesting user data for ID: {user_id} via RabbitMQ")
        user_data = self.request_user_from_service(user_id)

        if not user_data:
            logger.error(f"User not found for ID: {user_id}")
            raise AuthenticationFailed("User not found")

        logger.info(f"Successfully retrieved user data: {user_data}")
        return SimpleNamespace(**user_data, is_authenticated=True)

    def request_user_from_service(self, user_id):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
            channel = connection.channel()
            request_queue = "get_user"
            response_queue = "get_user_response"
            channel.queue_declare(queue=request_queue, durable=True)
            channel.queue_declare(queue=response_queue, durable=True)

            message = json.dumps({"user_id": user_id})
            channel.basic_publish(exchange="", routing_key=request_queue, body=message)
            logger.info(f"Sent user request for ID: {user_id}")

            method_frame, header_frame, body = channel.basic_get(queue=response_queue, auto_ack=True)
            connection.close()

            if body:
                response_data = json.loads(body)
                logger.info(f"Received response: {response_data}")
                return response_data
            else:
                logger.warning("No response received from RabbitMQ")
        except Exception as e:
            logger.error(f"RabbitMQ error: {str(e)}")
        return None