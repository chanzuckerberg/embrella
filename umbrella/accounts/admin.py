from django import forms
from django.contrib import admin
from django.contrib.auth.models import User

from .bots import BOT_PREFIX, BotState, create_bot, set_active
from .models import Bot, Profile, SystemFeatureFlag, UserClusterCredentials


@admin.register(SystemFeatureFlag)
class SystemFeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "description")
    list_editable = ("enabled",)  # toggle on/off straight from the list
    search_fields = ("name", "description")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "orcid_authenticated", "feature_flags_summary", "updated_at")
    search_fields = ("user__username", "user__email", "orcid_authenticated")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Feature flags")
    def feature_flags_summary(self, obj):
        flags = obj.feature_flags or {}
        if not flags:
            return "—"
        enabled = [name for name, value in flags.items() if value]
        summary = ", ".join(enabled) if enabled else "none on"
        return f"{len(enabled)}/{len(flags)} on: {summary}"


@admin.register(UserClusterCredentials)
class UserClusterCredentialsAdmin(admin.ModelAdmin):
    list_display = ("user", "cluster", "username", "updated_at")
    list_filter = ("cluster",)
    search_fields = ("user__username", "user__email", "username")
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at",)


class BotAddForm(forms.ModelForm):
    owner = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True, profile__bot_owner__isnull=True))

    class Meta:
        model = Bot
        fields = ("username", "first_name")
        labels = {"first_name": "Name"}
        help_texts = {"username": f"'{BOT_PREFIX}' is added if missing, e.g. hydra-1 → {BOT_PREFIX}hydra-1."}

    def clean_username(self):
        username = self.cleaned_data["username"]
        return username if username.startswith(BOT_PREFIX) else BOT_PREFIX + username


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    """Bots: token-only users owned by a person. Add one, then give it a token below."""

    list_display = ("username", "first_name", "owner", "is_active")
    search_fields = ("username", "first_name")
    actions = ("enable", "disable")

    def get_queryset(self, request):
        return (
            super().get_queryset(request).filter(profile__bot_owner__isnull=False).select_related("profile__bot_owner")
        )

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = BotAddForm
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("username", "first_name", "owner")
        return ("username", "first_name", "is_active")

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)
        bot = create_bot(form.cleaned_data["owner"], obj.username, obj.first_name)
        obj.pk = bot.pk

    @admin.display(description="Owner")
    def owner(self, obj):
        return obj.profile.bot_owner

    @admin.action(description="Enable selected bots")
    def enable(self, request, queryset):
        for bot in queryset:
            set_active(bot, BotState.ACTIVE)

    @admin.action(description="Disable selected bots")
    def disable(self, request, queryset):
        for bot in queryset:
            set_active(bot, BotState.DISABLED)
