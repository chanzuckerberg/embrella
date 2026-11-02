from accounts.feature_flags import is_feature_enabled
from rest_framework.permissions import SAFE_METHODS, BasePermission

from images.constants import IMAGES_FLAG


class ImagesEnabled(BasePermission):
    """Writes (upload, notes, delete) need the `images` feature flag; reads don't."""

    message = "Images are not enabled for this account."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return is_feature_enabled(request.user, IMAGES_FLAG)
