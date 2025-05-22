from django.contrib.auth.views import LoginView
from .forms import EmailLoginForm
from rest_framework.authtoken.views import ObtainAuthToken

class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        # Override to use email instead of username
        request.data['username'] = request.data.get('email')
        return super().post(request, *args, **kwargs)


class StaffLoginView(LoginView):
    authentication_form = EmailLoginForm
    template_name = 'login.html'