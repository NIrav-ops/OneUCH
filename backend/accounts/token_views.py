from rest_framework.exceptions import (
    AuthenticationFailed,
)
from rest_framework.permissions import (
    AllowAny,
)
from rest_framework.throttling import (
    ScopedRateThrottle,
)
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)

from accounts.authentication import (
    GENERIC_LOGIN_ERROR,
    authenticate_work_email,
)
from accounts.authentication_events import (
    record_authentication_success,
)
from accounts.models import (
    AUTH_METHOD_WORK_EMAIL,
)


class OneUCHTokenObtainPairSerializer(
    TokenObtainPairSerializer
):

    def validate(
        self,
        attrs,
    ):

        email = attrs.get(
            self.username_field
        )

        password = attrs.get(
            "password"
        )

        user = authenticate_work_email(
            email=email,
            password=password,
        )

        if user is None:

            raise AuthenticationFailed(
                GENERIC_LOGIN_ERROR
            )

        self.user = user

        refresh = self.get_token(
            user
        )

        record_authentication_success(
            user=user,
            method=(
                AUTH_METHOD_WORK_EMAIL
            ),
        )

        return {
            "refresh": str(
                refresh
            ),
            "access": str(
                refresh.access_token
            ),
        }


class OneUCHTokenObtainPairView(
    TokenObtainPairView
):

    serializer_class = (
        OneUCHTokenObtainPairSerializer
    )

    authentication_classes = []

    permission_classes = [
        AllowAny,
    ]

    throttle_classes = [
        ScopedRateThrottle,
    ]

    throttle_scope = "login"
