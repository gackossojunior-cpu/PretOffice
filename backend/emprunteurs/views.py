from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from config.mixins import LenderScopedQuerysetMixin
from .models import Borrower
from .serializers import BorrowerSerializer
from preteurs.permissions import HasLenderProfile


class BorrowerListView(LenderScopedQuerysetMixin, generics.ListAPIView):
    serializer_class = BorrowerSerializer
    permission_classes = [IsAuthenticated, HasLenderProfile]
    queryset = Borrower.objects.all()
    query_filter_fields = {
        "created_after": "created_at__date__gte",
        "created_before": "created_at__date__lte",
    }
    ordering_fields = ("created_at", "id", "first_name", "last_name")
    default_ordering = ("created_at",)


class BorrowerDetailView(LenderScopedQuerysetMixin, generics.RetrieveUpdateAPIView):
    serializer_class = BorrowerSerializer
    permission_classes = [IsAuthenticated, HasLenderProfile]
    queryset = Borrower.objects.all()
