from django.contrib import admin
from django.urls import path, include
from Account_Management.views import CustomObtainAuthToken

urlpatterns = [
    path('accounts/', include('Account_Management.urls')),  
    path('', include('Main.urls')),           
    path('admin/', admin.site.urls),
    path('api/', include('API.urls')),
    path('api-token-auth/', CustomObtainAuthToken.as_view(), name='api_token_auth'),
]

