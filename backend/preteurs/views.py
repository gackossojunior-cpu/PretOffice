from django.shortcuts import render
from rest_framework import generics
from rest_framework.exceptions import NotFound
from .permissions import IsLender
from .models import LenderProfile
from .serializers import LenderProfileSerializer

class MyLenderProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = LenderProfileSerializer
    permission_classes = [IsLender]

    def get_object(self):
        profile = LenderProfile.objects.filter(user=self.request.user).first()
        if profile is None:
            raise NotFound("Aucun profil prêteur n'est associé à cet utilisateur.")
        return profile
