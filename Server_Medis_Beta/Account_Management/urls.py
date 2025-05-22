from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import StaffLoginView

urlpatterns = [
    path('login/', StaffLoginView.as_view(), name='staff-login'),
    path('logout/', LogoutView.as_view(next_page='staff-login'), name='logout'),
    path('', StaffLoginView.as_view(), name='staff-login'),  # Redirect to login page if no path is provided
]
