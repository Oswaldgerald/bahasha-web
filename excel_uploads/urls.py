from rest_framework.routers import DefaultRouter
from .views import ExcelUploadViewSet

router = DefaultRouter()
router.register(r"excel-uploads", ExcelUploadViewSet, basename="excel-uploads")

urlpatterns = router.urls