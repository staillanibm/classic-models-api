from django.conf import settings
from django.db import models


class CustomerProfile(models.Model):
    """Links a Django user to a classicmodels Customer for RBAC ownership checks."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    # Plain integer, not a ForeignKey: classicmodels.Customer lives in an
    # unmanaged, separately-owned table (managed = False), so we reference it
    # by value rather than joining across schemas.
    customernumber = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.user} -> customer {self.customernumber}"


class ExternalIdentity(models.Model):
    """
    Links a Django user to a stable external OIDC IdP subject (`sub` claim).

    `sub` is the lookup key (immutable), while the linked User's username
    mirrors the IdP's `preferred_username` for readability in /admin and logs
    — it is refreshed on each login in case the display name changes upstream.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="external_identity",
    )
    sub = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user} -> sub {self.sub}"
