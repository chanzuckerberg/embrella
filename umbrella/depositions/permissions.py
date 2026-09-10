"""permissions for the depositions submission."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import (
    Dataset,
    Deposition,
    DepositionSession,
)


def deposition_owner_id(obj):
    if isinstance(obj, Deposition):
        return obj.submitter_user_id
    if isinstance(obj, Dataset):
        return obj.deposition.submitter_user_id
    if isinstance(obj, DepositionSession):
        return obj.dataset.deposition.submitter_user_id
    return None


class IsDepositionOwnerOrReadOnly(BasePermission):
    message = "Only the submitter of this deposition can modify it."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner_id = deposition_owner_id(obj)
        return owner_id is not None and owner_id == request.user.id
