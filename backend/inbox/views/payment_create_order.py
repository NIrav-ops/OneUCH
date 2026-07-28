from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings

from inbox.models import BillingPlan
from inbox.payments.razorpay_client import get_razorpay_client


class CreatePaymentOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_code = request.data.get("plan_code")

        if not plan_code:
            return Response(
                {"error": "plan_code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            plan = BillingPlan.objects.get(
                code=plan_code,
                is_active=True,
            )
        except BillingPlan.DoesNotExist:
            return Response(
                {"error": "Invalid plan"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if plan.price_monthly <= 0:
            return Response(
                {"error": "This plan does not require payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Temporary safeguard (Phase 4.3 – dev mode)
        if settings.RAZORPAY_KEY_ID.startswith("rzp_test_dummy"):
            return Response(
        {
            "message": "Payment gateway not configured yet",
            "plan": {
                "code": plan.code,
                "name": plan.name,
                "price": plan.price_monthly,
                    },
                },
                status=status.HTTP_200_OK,
            )
        client = get_razorpay_client()

        order = client.order.create(
            {
                "amount": int(plan.price_monthly * 100),  # paise
                "currency": "INR",
                "receipt": f"plan_{plan.code}",
                "payment_capture": 1,
            }
        )

        return Response(
            {
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "plan": {
                    "code": plan.code,
                    "name": plan.name,
                    "price": plan.price_monthly,
                },
            },
            status=status.HTTP_200_OK,
        )
