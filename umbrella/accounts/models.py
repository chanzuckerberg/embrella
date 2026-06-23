from django.conf import settings
from django.db import models


class UserClusterCredentials(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cluster_credentials",
    )
    cluster = models.ForeignKey("stores.Cluster", on_delete=models.CASCADE)
    username = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounts"
        db_table = "users_userclustercredentials"
        unique_together = ("user", "cluster")
        verbose_name_plural = "User cluster credentials"

    def __str__(self):
        return f"{self.user.username} @ {self.cluster_id} = {self.username}"
