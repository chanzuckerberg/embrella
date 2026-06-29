from django.contrib import admin

from .models import Institution, Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("family_name", "given_name", "orcid", "contact_email", "institution", "user", "updated_at")
    search_fields = ("given_name", "family_name", "orcid", "contact_email", "user__username")
    list_filter = ("institution",)
    autocomplete_fields = ("user", "institution")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "ror_id", "city", "country", "updated_at")
    search_fields = ("name", "ror_id", "city", "country")
    readonly_fields = ("created_at", "updated_at")
