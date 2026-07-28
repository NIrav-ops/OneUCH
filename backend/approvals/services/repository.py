from django.db import transaction

from approvals.models import ApprovalItem
from approvals.services.base_repository import BaseRepository
from approvals.services.validator import ApprovalValidator


class ApprovalRepository(BaseRepository):

    model = ApprovalItem

    @classmethod
    @transaction.atomic
    def create_request(cls, **data):

        ApprovalValidator.validate_create(data)

        data.setdefault(
            "source_type",
            "workflow",
        )

        return cls.create(**data)

    @classmethod
    def approve(cls, request):

        request.status = "approved"

        return cls.save(request)

    @classmethod
    def reject(cls, request):

        request.status = "rejected"

        return cls.save(request)