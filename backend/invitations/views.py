from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Invitations
from .serializers import InvitationSerializer, PublicInvitationSerializer
from emprunteurs.models import Borrower
from emprunteurs.serializers import PublicBorrowerApplicationSerializer
from rest_framework.response import Response

class InvitationListCreateView(generics.ListCreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invitations.objects.filter(lender=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            lender=self.request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )

class PublicInvitationDetailView(generics.RetrieveAPIView):
    serializer_class = PublicInvitationSerializer
    permission_classes = [AllowAny]
    
    lookup_field = "token"
    lookup_url_kwargs = "token"

    def get_queryset(self):
        return Invitations.objects.all()

    def retrieve(self, request, *args, **kwargs):
        invitation = self.get_object()

        if invitation.status == "ACTIVE":
            if timezone.now() >= invitation.expires_at:
                invitation.status = "EXPIRED"
                invitation.save(update_fields=["status"])

        if invitation.status != "ACTIVE":
            return Response(
                {
                    "detail": "Cette invitation n'est plus valide.",
                    "status": invitation.status,
                },
                status=400,
            )
        
        serializer = self.get_serializer(invitation)

        return Response(serializer.data)

class PublicInvitationApplicationView(generics.CreateAPIView):
    serializer_class = PublicBorrowerApplicationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        token = kwargs.get("token")

        try:
            invitation = Invitations.objects.get(token=token)
        except Invitations.DoesNotExist:
            return Response(
                {
                    "detail": "Cette invitation n'existe pas."
                },
                status=404,
            )

        if invitation.status != "ACTIVE":
            return Response(
                {
                    "detail": "Cette invitation n'est plus valide.",
                    "status": invitation.status,
                },
                status=400,
            )

        if timezone.now() >= invitation.expires_at:
            invitation.status = "EXPIRED"
            invitation.save(update_fields=["status"])

            return Response(
                {
                    "detail": "Cette invitation a expiré."
                },
                status=400,
            )
        
        if invitation.borrower is not None:
            return Response(
                {
                    "detail": "Cette invitation a déjà été utilisée."
                },
                status=400,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        borrower = serializer.save(
            lender=invitation.lender
        )

        invitation.borrower = borrower
        invitation.status = "USED"
        invitation.used_at = timezone.now()
        invitation.save(
            update_fields=[
                "borrower",
                "status",
                "used_at",
            ]
        )

        return Response(
            {
                "detail": "Votre demande a été enregistrée avec succès.",
                "borrower_id": borrower.id,
            },
            status=201,
        )
