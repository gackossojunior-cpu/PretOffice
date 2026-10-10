from django.http import request
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from .models import LoanApplication
from .serializers import LoanApplicationSerializer


class HasLenderProfile(BasePermission):
    message = "Un profil prêteur est requis pour accéder aux demandes de prêt."

    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated
            and user.role == "LENDER"
            and hasattr(user, "lender_profile")
        )


class LoanApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = LoanApplicationSerializer
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]

    def get_queryset(self):
        return LoanApplication.objects.filter(borrower__lender=self.request.user)

class LoanDecisionView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]

    def post(self, request, pk):
        try:
            loan = LoanApplication.objects.get(
                pk=pk,
                borrower__lender=self.request.user,
            )
        except LoanApplication.DoesNotExist:
            return Response({"detail": "Demande de prêt non trouvée."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        reason = request.data.get("reason", "")

        if loan.status != "PENDING":
            return Response({"detail": "La demande de prêt a déjà été traitée."}, status=status.HTTP_400_BAD_REQUEST)

        if action == "APPROVE":
            loan.status = "APPROVED"
            loan.decision_reason = reason
            loan.save()
            return Response({"detail": "Demande de prêt approuvée."}, status=status.HTTP_200_OK)
        
        elif action == "REJECT":
            loan.status = "REJECTED"
            loan.decision_reason = reason
            loan.save()
            return Response({"detail": "Demande de prêt rejetée."}, status=status.HTTP_200_OK)

        return Response({"detail": "Action invalide."}, status=status.HTTP_400_BAD_REQUEST)