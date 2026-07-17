from django.contrib import admin

from .models import CustomerProfile, ExternalIdentity


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "customernumber")
    search_fields = ("user__username", "customernumber")


@admin.register(ExternalIdentity)
class ExternalIdentityAdmin(admin.ModelAdmin):
    list_display = ("user", "sub")
    search_fields = ("user__username", "sub")
