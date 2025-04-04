


import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import pika
import uuid
import time
import asyncio
logger = logging.getLogger(__name__)
room_offers = {}  # Store offers for late-joining peers

class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.group_name = f'videocall_{self.room_name}'
        query_string = self.scope['query_string'].decode()
        params = dict(qp.split('=') for qp in query_string.split('&') if qp)
        self.role = params.get('role')
        self.email = params.get('email') if self.role == "doctor" else None
        self.slot = params.get('slot') if self.role == "doctor" else None
        self.date = params.get('date') if self.role == "doctor" else None
        self.ws_base_url = "ws://localhost:8004"

        if not self.role:
            logger.warning(f"Missing role for {self.channel_name}, closing connection")
            await self.close()
            return

        if self.role == "doctor" and (not self.email or not self.date or not self.slot):
            logger.warning(f"Missing email, date, or slot for doctor at {self.channel_name}")
            await self.close()
            return

        logger.info(f"Starting connection to {self.group_name} as {self.role} ({self.channel_name})")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"Connection accepted successfully: {self.channel_name}")

        meet_link = f"{self.ws_base_url}/ws/video_call/{self.room_name}/?role={self.role}"
        if self.role == "doctor":
            meet_link += f"&email={self.email}"
        success = await self.save_or_update_room(meet_link)
        if not success:
            logger.error(f"Failed to save/update room {self.room_name}")
            await self.send(text_data=json.dumps({"error": "Failed to save room"}))
            await self.close(code=4001)
            return

        await self.send(text_data=json.dumps({"status": "connected", "meet_link": meet_link}))
        logger.info(f"Sent connected message to {self.channel_name}")

        await self.channel_layer.group_send(
            self.group_name,
            {"type": "user_joined", "role": self.role}
        )
        logger.info(f"Group send completed for {self.group_name}")

        # If there's a stored offer and this is the patient, send it to them
        if self.role == "patient":
            stored_offer = await self.get_stored_offer()
            if stored_offer:
                await self.send(text_data=json.dumps(stored_offer))
                logger.info(f"Sent stored offer to late-joining patient in {self.room_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"Disconnected from {self.group_name}: {self.channel_name}, Code: {close_code}")
            if self.role == "doctor":
                asyncio.create_task(self.run_wallet_update())
                logger.info(f"Scheduled WalletUpdate for room {self.room_name}")
    async def run_wallet_update(self):
        success = await self.WalletUpdate()
        if success:
            logger.info(f"Successfully processed call end for room {self.room_name}")
        else:
            logger.error(f"Failed to process call end for room {self.room_name}")
    async def receive(self, text_data):
        logger.info(f"Received message in {self.group_name} ({self.channel_name}): {text_data}")
        message = json.loads(text_data)

        if "offer" in message:
            await self.store_offer(message)
            logger.info(f"Broadcasting offer to group {self.group_name}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "send_message",
                    "message": message,
                    "sender_channel_name": self.channel_name,
                }
            )
        elif "answer" in message:
            logger.info(f"Received answer in {self.group_name} from {self.channel_name}: {message}")
            logger.info(f"Broadcasting answer to group {self.group_name}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "send_message",
                    "message": message,
                    "sender_channel_name": self.channel_name,
                }
            )
        elif "candidate" in message:
            logger.info(f"Received candidate in {self.group_name} from {self.channel_name}: {message}")
            logger.info(f"Broadcasting candidate to group {self.group_name}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "send_message",
                    "message": message,
                    "sender_channel_name": self.channel_name,
                }
            )

    async def send_message(self, event):
        message = event["message"]
        sender_channel_name = event["sender_channel_name"]
        if sender_channel_name != self.channel_name:
            logger.info(f"Sending message to {self.channel_name} from {sender_channel_name}: {message}")
            await self.send(text_data=json.dumps(message))

    async def user_joined(self, event):
        role = event["role"]
        await self.send(text_data=json.dumps({"user_joined": True, "role": role}))

    @sync_to_async
    def save_or_update_room(self, meet_link):
        roomname = self.room_name
        logger.info(f"Processing room {roomname} for {self.role}")
        correlation_id = str(uuid.uuid4())
        rabbitmq_response = None

        if self.role == "doctor":
            try:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host="rabbitmq", heartbeat=600, blocked_connection_timeout=300)
                )
                channel = connection.channel()
                channel.queue_declare(queue="roomupdate")
                response_queue = channel.queue_declare(queue="", exclusive=True)
                response_queue_name = response_queue.method.queue
                channel.basic_qos(prefetch_count=1)

                def on_response(ch, method, properties, body):
                    nonlocal rabbitmq_response
                    try:
                        if properties.correlation_id == correlation_id:
                            rabbitmq_response = json.loads(body)
                            logger.info(f"Received RabbitMQ response: {rabbitmq_response}")
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON response from RabbitMQ")

                channel.basic_consume(queue=response_queue_name, on_message_callback=on_response, auto_ack=True)
                request_data = json.dumps({
                    "room_name": roomname,
                    "email": self.email,
                    "slot": self.slot,
                    "date": self.date
                })
                channel.basic_publish(
                    exchange="",
                    routing_key="roomupdate",
                    properties=pika.BasicProperties(reply_to=response_queue_name, correlation_id=correlation_id),
                    body=request_data,
                )
                logger.info(f"Sent RabbitMQ request: {request_data}")

                timeout = time.time() + 10
                while rabbitmq_response is None and time.time() < timeout:
                    try:
                        connection.process_data_events(time_limit=1)
                    except pika.exceptions.AMQPConnectionError:
                        logger.error("RabbitMQ connection lost while waiting for response")
                        return False

                if rabbitmq_response is None:
                    logger.warning("No response from User_Service")
                    return False

                if rabbitmq_response.get("error"):
                    logger.error(f"Room validation failed: {rabbitmq_response['error']}")
                    return False

                logger.info(f"Room {roomname} saved/updated successfully for doctor")
                return True

            except pika.exceptions.AMQPConnectionError:
                logger.error("RabbitMQ service unavailable")
                return False
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return False
            finally:
                if "connection" in locals() and connection.is_open:
                    connection.close()
        else:  # Patient role
            logger.info(f"Patient joining room {roomname}, no update needed")
            return True
        
    @sync_to_async
    def WalletUpdate(self):
        roomname = self.room_name
        logger.info(f"Processing room {roomname} for {self.role}")
        correlation_id = str(uuid.uuid4())
        rabbitmq_response = None
        logger.info({"emaill doctor":self.email})
        if self.role == "doctor":
            try:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host="rabbitmq", heartbeat=600, blocked_connection_timeout=300)
                )
                channel = connection.channel()
                channel.queue_declare(queue="walletadd")
                response_queue = channel.queue_declare(queue="", exclusive=True)
                response_queue_name = response_queue.method.queue
                channel.basic_qos(prefetch_count=1)

                def on_response(ch, method, properties, body):
                    nonlocal rabbitmq_response
                    try:
                        if properties.correlation_id == correlation_id:
                            rabbitmq_response = json.loads(body)
                            logger.info(f"Received RabbitMQ response: {rabbitmq_response}")
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON response from RabbitMQ")

                channel.basic_consume(queue=response_queue_name, on_message_callback=on_response, auto_ack=True)
                request_data = json.dumps({
                    "email": self.email,
                    "slot": self.slot,
                    "date": self.date
                })
                channel.basic_publish(
                    exchange="",
                    routing_key="walletadd",
                    properties=pika.BasicProperties(reply_to=response_queue_name, correlation_id=correlation_id),
                    body=request_data,
                )
                logger.info(f"Sent RabbitMQ request: {request_data}")

                timeout = time.time() + 10
                while rabbitmq_response is None and time.time() < timeout:
                    try:
                        connection.process_data_events(time_limit=1)
                    except pika.exceptions.AMQPConnectionError:
                        logger.error("RabbitMQ connection lost while waiting for response")
                        return False

                if rabbitmq_response is None:
                    logger.warning("No response from User_Service")
                    return False

                if rabbitmq_response.get("error"):
                    logger.error(f"Room validation failed: {rabbitmq_response['error']}")
                    return False

                logger.info(f"Room {roomname} saved/updated successfully for doctor")
                return True

            except pika.exceptions.AMQPConnectionError:
                logger.error("RabbitMQ service unavailable")
                return False
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return False
            finally:
                if "connection" in locals() and connection.is_open:
                    connection.close()
        else:  # Patient role
            logger.info(f"Patient joining room {roomname}, no update needed")
            return True

    @sync_to_async
    def store_offer(self, message):
        room_offers[self.room_name] = message
        logger.info(f"Stored offer in {self.room_name}: {message}")

    @sync_to_async
    def get_stored_offer(self):
        offer = room_offers.get(self.room_name)
        if offer:
            logger.info(f"Retrieved stored offer in {self.room_name}: {offer}")
        else:
            logger.warning(f"No stored offer found in {self.room_name}")
        return offer


