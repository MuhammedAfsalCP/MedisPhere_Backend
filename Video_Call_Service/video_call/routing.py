# from django.urls import re_path
# from .consumers import VideoCallConsumer

# websocket_urlpatterns = [
#     re_path(r'ws/video_call/(?P<room_name>\w+)/$', VideoCallConsumer.as_asgi()),
# ]

# from django.urls import re_path
# from . import consumers

# websocket_urlpatterns = [
#     re_path(r"ws/video_call/(?P<room_name>\w+)/$", consumers.VideoCallConsumer.as_asgi()),
# ]

# VideoCallService/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/video_call/(?P<room_name>[\w.-]+)/$', consumers.VideoCallConsumer.as_asgi()),
]