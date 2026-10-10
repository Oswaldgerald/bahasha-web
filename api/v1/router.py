from django.db import connection
from ninja import Router

from categories.api.router import router as categories_router
from contributions.api.router import router as contributions_router
from members.api.router import router as members_router
from notifications.api.router import router as notifications_router
from payments.api.router import router as payments_router
from users.api.router import router as auth_router


router = Router()


@router.get("/health", auth=None, tags=["platform"])
def api_health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "database": "available",
    }


router.add_router("/auth", auth_router)
router.add_router("", members_router)
router.add_router("", categories_router)
router.add_router("", contributions_router)
router.add_router("", notifications_router)
router.add_router("", payments_router)
