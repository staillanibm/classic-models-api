from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class JWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "authentication.oidc_auth.OIDCJWTAuthentication"
    name = "JWTAuth"

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(
            header_name="Authorization", token_prefix="Bearer", bearer_format="JWT"
        )


class ApiKeyAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "authentication.api_key_auth.ApiKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication using X-API-Key header",
        }
