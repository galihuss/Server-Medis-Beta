from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User # Import your custom User model
from .forms import CustomUserCreationForm, CustomUserChangeForm # Import your custom forms
from django.utils.translation import gettext_lazy as _

class CustomUserAdmin(UserAdmin):
    """
    Custom UserAdmin for the User model.
    Uses the custom forms to handle password hashing.
    """
    form = CustomUserChangeForm # Use this form when changing an existing user
    add_form = CustomUserCreationForm # Use this form when adding a new user
    model = User # Link the admin to your custom User model

    # Override the default fieldsets from UserAdmin to match your model
    # The password field will be handled by the forms
    fieldsets = (
        (None, {'fields': ('email', 'password')}), # 'password' field included for consistency, though handled by form link
        # Add other custom fields here if you have them
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        # (_('Important dates'), {'fields': ('last_login', 'date_joined')}), # Commented out as it caused an error when editing
    )

    # Define the fieldsets specifically for the add form
    # This one should work fine as it doesn't include last_login/date_joined
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'password2'), # password and password2 for confirmation
        }),
    )

    # Define what fields appear in the list view
    list_display = ('email', 'is_active', 'is_staff', 'is_superuser')
    # Define fields that can be used for searching
    search_fields = ('email',)
    # Define default ordering
    ordering = ('email',)
    # Define fields that use the horizontal filter widget
    filter_horizontal = ('groups', 'user_permissions') # Keep if you use PermissionsMixin


# Register your custom User model with your custom admin class
admin.site.register(User, CustomUserAdmin)
