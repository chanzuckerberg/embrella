"""Keep project role groups in sync with memberships, including admin edits."""

from django.contrib.auth.models import Group
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from projects import services
from projects.models import Project, ProjectMembership


@receiver(post_save, sender=Project)
def _setup_project(sender, instance, raw=False, **kwargs):
    if raw:
        return

    services.ensure_groups(instance)
    services.ensure_leader(instance)


@receiver(post_delete, sender=Project)
def _drop_groups(sender, instance, **kwargs):
    Group.objects.filter(id__in=[instance.viewer_group_id, instance.editor_group_id]).delete()


@receiver(pre_save, sender=ProjectMembership)
def _track_user(sender, instance, raw=False, **kwargs):
    # Admin inlines can reassign a membership to another user; remember who to clear.
    instance._old_user_id = None
    if raw or instance.pk is None:
        return

    instance._old_user_id = ProjectMembership.objects.filter(pk=instance.pk).values_list("user_id", flat=True).first()


@receiver(post_save, sender=ProjectMembership)
def _sync_member(sender, instance, raw=False, **kwargs):
    if raw:
        return

    old_user_id = getattr(instance, "_old_user_id", None)
    if old_user_id and old_user_id != instance.user_id:
        services.clear_groups(instance.project, old_user_id)

    services.sync_groups(instance)


@receiver(post_delete, sender=ProjectMembership)
def _clear_member(sender, instance, **kwargs):
    project = Project.objects.filter(pk=instance.project_id).first()
    if project is None:
        return

    services.clear_groups(project, instance.user_id)
