from django.db import models
from django.conf import settings
User = settings.AUTH_USER_MODEL

# Create your models here.
class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Patients(models.Model):
    JENIS_KELAMIN = [
        (0, 'Perempuan'),
        (1, 'Laki-laki'),
        (2, 'Non-biner')
    ]
    patient_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    kelamin = models.PositiveSmallIntegerField(choices=JENIS_KELAMIN
                                                , help_text="0: perempuan, 1: laki-laki, 2: non-biner")
    tanggal_lahir = models.DateField()
    phone_number = models.CharField(max_length=100, help_text="nomor telpon indonesia")
    alamat = models.TextField(blank=True)
    

    def __str__(self):
        return f"{self.patient_id}: {self.name}"
    
class Readings(models.Model):
    DEHIDRASI = [
        (0, 'Dehidrasi Berat'),
        (1, 'Dehidrasi Sedang'),
        (2, 'Dehidrasi Ringan'),
        (3, 'Cukup'),
        (4, 'Baik')
    ]
    timestamp = models.DateTimeField()
    patient_id = models.ForeignKey(Patients, on_delete=models.CASCADE, related_name="readings")
    temperature = models.FloatField()
    alcohol = models.FloatField()
    urine = models.PositiveSmallIntegerField(choices=DEHIDRASI)
    berat = models.FloatField()
    tinggi = models.FloatField()

    def __str__(self):
        return f"{self.timestamp}: {self.patient_id}"

class Nodes(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('reading', 'Reading'),
        ('error', 'Error'),
        ('offline', 'Offline'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    assigned_patient = models.ForeignKey(Patients, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_node")
    assigned_at = models.DateTimeField(null=True, blank=True)
    user = models.OneToOneField('Account_Management.User', on_delete=models.CASCADE) 

    def __str__(self):
         return f"Node {self.pk} ({self.status})" # Gunakan self.pk untuk primary key
