from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import AllowAny

from .views import health_view

# All URLs are served under /classic-models base path
urlpatterns = [
    path("classic-models/health/", health_view, name="health"),
    path("classic-models/admin/", admin.site.urls),
    path("classic-models/api/v1/", include("api.v1.urls")),
    path("classic-models/api/auth/", include("authentication.urls")),
    # OpenAPI schema and docs (public access)
    path(
        "classic-models/api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "classic-models/api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema", permission_classes=[AllowAny]
        ),
        name="swagger-ui",
    ),
    path(
        "classic-models/api/redoc/",
        SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="redoc",
    ),
]
