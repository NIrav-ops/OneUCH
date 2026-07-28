from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from asgiref.sync import sync_to_async
from django.db import close_old_connections
from django.conf import settings
import jwt


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        close_old_connections()

        # 🔥 Lazy imports (VERY IMPORTANT)
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.auth import get_user_model

        User = get_user_model()

        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)

        token = query_params.get("token")

        if token:
            try:
                token = token[0]

                decoded_data = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"]
                )

                user = await sync_to_async(User.objects.get)(
                    id=decoded_data["user_id"]
                )

                scope["user"] = user

            except Exception as e:
                print("JWT WS ERROR:", str(e))
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)