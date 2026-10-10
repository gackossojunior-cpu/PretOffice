from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Borrower
from .serializers import BorrowerSerializer


class BorrowerListView(generics.ListAPIView):
    serializer_class = BorrowerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Borrower.objects.filter(
            lender=self.request.user
        ).order_by("created_at")
    
