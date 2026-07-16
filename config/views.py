from django.db import connection
from django.db.utils import OperationalError
from django.http import JsonResponse


def health_view(request):
    """Liveness/readiness probe target: verifies the app can reach its database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})
