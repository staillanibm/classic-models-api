"""
JWT authentication for tokens issued by an external OIDC IdP (Keycloak,
Auth0, Entra ID, etc. — any IdP following standard OIDC claim conventions).

Verification (signature, expiry, issuer, audience) is handled by SimpleJWT
itself via JWK_URL/ISSUER/AUDIENCE (see config.settings.base). This module
only overrides *user resolution*: instead of looking up a local user_id
claim (which an external IdP has no reason to know about), it resolves the
Django user from the token's `sub` claim, provisioning one just-in-time on
first sight, and syncs the user's Django Groups from a configurable roles
claim (JWT_ROLES_CLAIM_PATH) on every request.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings

from .jwt_tokens import CustomAccessToken
from .models import ExternalIdentity

User = get_user_model()


class ExternalOrInternalAccessToken(CustomAccessToken):
    """
    Accepts both this app's own access tokens (which carry TOKEN_TYPE_CLAIM,
    checked normally) and external-IdP tokens (an IdP has no reason to set
    that claim, so its absence alone must not fail verification).
    """

    def verify(self, *args, **kwargs):
        if api_settings.TOKEN_TYPE_CLAIM not in self.payload:
            self.payload[api_settings.TOKEN_TYPE_CLAIM] = self.token_type
        super().verify(*args, **kwargs)


def _get_claim_path(payload: dict, dotted_path: str):
    value = payload
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _extract_roles(validated_token) -> list[str]:
    path = getattr(settings, "JWT_ROLES_CLAIM_PATH", "realm_access.roles")
    # validated_token is a SimpleJWT Token object, not a plain dict — its
    # actual claims live in .payload.
    roles = _get_claim_path(validated_token.payload, path)
    if not isinstance(roles, list):
        return []
    return [r for r in roles if isinstance(r, str)]


class OIDCJWTAuthentication(JWTAuthentication):
    """
    Resolves users from an external IdP's `sub` claim (JIT provisioning) and
    syncs Django Group membership from the token's roles claim on each request.

    Tokens minted by this app's own login/refresh flow (authentication.views)
    carry a `user_id` claim and are resolved the standard SimpleJWT way
    instead — only tokens without it (i.e. issued by an external IdP) go
    through JIT provisioning.
    """

    def get_validated_token(self, raw_token):
        try:
            return ExternalOrInternalAccessToken(raw_token)
        except TokenError as e:
            raise InvalidToken(e.args[0])

    def get_user(self, validated_token):
        if validated_token.get(api_settings.USER_ID_CLAIM):
            return super().get_user(validated_token)

        sub = validated_token.get("sub")
        if not sub:
            raise AuthenticationFailed("Token contains no 'sub' claim.")

        preferred_username = validated_token.get("preferred_username") or sub

        with transaction.atomic():
            identity = (
                ExternalIdentity.objects.select_related("user")
                .filter(sub=sub)
                .first()
            )
            if identity is None:
                user = User.objects.create(
                    username=self._unique_username(preferred_username),
                    email=validated_token.get("email", "") or "",
                )
                identity = ExternalIdentity.objects.create(user=user, sub=sub)
            user = identity.user

            # Keep the displayed username in sync with the IdP in case it
            # changes there; `sub` (the lookup key) never changes.
            if (
                preferred_username
                and user.username != preferred_username
                and not User.objects.filter(username=preferred_username)
                .exclude(pk=user.pk)
                .exists()
            ):
                user.username = preferred_username
                user.save(update_fields=["username"])

            self._sync_roles(user, validated_token)

        if not user.is_active:
            raise AuthenticationFailed("User is inactive.")

        return user

    @staticmethod
    def _unique_username(preferred_username: str) -> str:
        """Suffix with -2, -3, ... if preferred_username is already taken by
        an unrelated User (e.g. locally created, or from a different sub)."""
        candidate = preferred_username
        suffix = 2
        while User.objects.filter(username=candidate).exists():
            candidate = f"{preferred_username}-{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _sync_roles(user, validated_token) -> None:
        role_names = set(_extract_roles(validated_token))
        # Superuser status set locally in Django (e.g. via /admin) is never
        # revoked by an IdP role sync — only group membership is managed here.
        current = set(user.groups.values_list("name", flat=True))
        if current == role_names:
            return

        groups = list(Group.objects.filter(name__in=role_names))
        user.groups.set(groups)
