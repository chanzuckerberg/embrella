from rest_framework import serializers

from .bots import Write, on_behalf_error


class OnBehalfMixin:
    """Bots must name the person they log work for in ``user``.

    POST grid (bot-hydra-1, user=alice) → CryoGrid.user = alice, history_user = bot-hydra-1
    """

    def run_validation(self, data=serializers.empty):
        value = super().run_validation(data)

        request = self.context.get("request")
        write = Write.CREATE if self.instance is None else Write.UPDATE
        error = on_behalf_error(getattr(request, "user", None), value.get("user"), write)
        if error:
            raise serializers.ValidationError({"user": error})
        return value
