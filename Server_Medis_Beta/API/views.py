from rest_framework import viewsets, permissions
from Main.models import Patients, Readings, Nodes
from .serializers import PatientSerializer, ReadingSerializer, NodeSerializer

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patients.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]

class ReadingViewSet(viewsets.ModelViewSet):
    queryset = Readings.objects.all()
    serializer_class = ReadingSerializer
    permission_classes = [permissions.IsAuthenticated]

class NodeViewSet(viewsets.ModelViewSet):
    queryset = Nodes.objects.all()
    serializer_class = NodeSerializer
    permission_classes = [permissions.IsAuthenticated]
