from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate

from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.

class LoginAPIView(APIView):
    permission_classes = []  # Allow login without token

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(
            request,
            username=email,
            password=password
        )

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })
