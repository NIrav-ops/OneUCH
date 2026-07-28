import os
import django

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from authentication.jwt_ws_middleware import JWTAuthMiddleware
import inbox.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

django.setup()

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({

    "http": django_asgi_app,

    "websocket": JWTAuthMiddleware(
        URLRouter(
            inbox.routing.websocket_urlpatterns
        )
    ),

})