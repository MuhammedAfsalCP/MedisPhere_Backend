import os
from django.core.asgi import get_asgi_application
from channels.application import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from video_call.routing import websocket_urlpatterns  # Adjust based on your app structure

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Video_Call_Service.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
