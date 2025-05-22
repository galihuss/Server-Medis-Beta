from django.urls import path
from . import views

urlpatterns = [
    path('', views.patient_info_view, name='patient-info'),
    path('patients/<str:patient_id>/', views.patient_dashboard_view, name='patient-dashboard'),
    path('assign-node/<int:patient_id>/', views.assign_node_view, name='assign-node'),
]
