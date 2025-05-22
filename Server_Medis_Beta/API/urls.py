from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, ReadingViewSet, NodeViewSet


router = DefaultRouter()
router.register(r'patients', PatientViewSet)
router.register(r'readings', ReadingViewSet)
router.register(r'nodes', NodeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
