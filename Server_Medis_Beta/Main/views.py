from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Patients, Nodes


def is_allowed(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.groups.filter(name=["Dokter", "Suster","Admin"]).exists())

@login_required
@user_passes_test(is_allowed)
def patient_info_view(request):
    patients = Patients.objects.all().order_by('patient_id')  # Order by patient_id
    return render(request, 'monitoring.html', {'patients': patients})

@login_required
@user_passes_test(is_allowed)
def patient_dashboard_view(request, patient_id):
    patient = get_object_or_404(Patients, patient_id=patient_id)
    latest_reading = patient.readings.last()
    bmi = None
    if latest_reading and latest_reading.tinggi > 0:
        bmi = latest_reading.berat / ((latest_reading.tinggi / 100) ** 2)
    return render(request, 'patient_dashboard.html', {
        'patient': patient,
        'bmi': bmi
    })

@csrf_exempt
@login_required
@user_passes_test(is_allowed)
def assign_node_view(request, patient_id):
    if request.method == 'POST':
        try:
            patient = get_object_or_404(Patients, patient_id=patient_id)
            # Find an available node
            node = Nodes.objects.filter(status='available').first()
            if not node:
                return JsonResponse({'message': 'No available nodes'}, status=400)

            # Assign the node to the patient
            node.status = 'assigned'
            node.assigned_patient = patient
            node.save()

            return JsonResponse({'message': 'Node successfully assigned to patient'})
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)
    return JsonResponse({'message': 'Invalid request method'}, status=405)