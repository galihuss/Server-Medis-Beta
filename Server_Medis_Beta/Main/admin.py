from django.contrib import admin
from .models import  Readings, Nodes, StaffProfile, Patients

# Register your models here.

admin.site.register(Patients)
admin.site.register(Readings)
admin.site.register(Nodes)
admin.site.register(StaffProfile)