from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from config.mixins import LenderScopedQuerysetMixin
from audit.services import record_audit_event
from emprunteurs.models import Borrower
from emprunteurs.serializers import PublicBorrowerApplicationSerializer
from preteurs.permissions import HasLenderProfile

from .models import Invitations
from .serializers import (
    InvitationRevokeResponseSerializer,
    InvitationSerializer,
    PublicInvitationSerializer,
)


INVALID_INVITATION_MESSAGE = "Cette invitation n'est pas valide."


class InvitationListCreateView(
    LenderScopedQuerysetMixin,
    generics.ListCreateAPIView,
):
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated, HasLenderProfile]
    queryset = Invitations.objects.all()
    query_filter_fields = {
        "status": "status",
        "created_after": "created_at__date__gte",
        "created_before": "created_at__date__lte",
        "expires_after": "expires_at__date__gte",
        "expires_before": "expires_at__date__lte",
    }
    ordering_fields = ("created_at", "expires_at", "status", "id")
    default_ordering = ("-created_at",)

    def perform_create(self, serializer):
        serializer.save(lender=self.request.user)


class InvitationDetailView(
    LenderScopedQuerysetMixin,
    generics.RetrieveAPIView,
):
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated, HasLenderProfile]
    queryset = Invitations.objects.all()


class InvitationRevokeView(
    LenderScopedQuerysetMixin,
    generics.GenericAPIView,
):
    permission_classes = [IsAuthenticated, HasLenderProfile]
    queryset = Invitations.objects.all()
    serializer_class = InvitationRevokeResponseSerializer

    @transaction.atomic
    @extend_schema(
        request=None,
        responses=InvitationRevokeResponseSerializer,
    )
    def post(self, request, pk):
        try:
            invitation = self.get_queryset().select_for_update().get(pk=pk)
        except Invitations.DoesNotExist as exc:
            raise NotFound("Invitation introuvable.") from exc

        if invitation.status != "PENDING":
            return Response(
                {"detail": "Cette invitation ne peut plus être révoquée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation.status = "REVOKED"
        invitation.save(update_fields=["status"])
        record_audit_event(
            request.user,
            "INVITATION_REVOKED",
            invitation,
        )
        return Response(
            {"detail": "Invitation révoquée."},
            status=status.HTTP_200_OK,
        )


class PublicInvitationDetailView(generics.RetrieveAPIView):
    serializer_class = PublicInvitationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_invitation"
    lookup_field = "token"
    lookup_url_kwarg = "token"
    queryset = Invitations.objects.all()

    def get_object(self):
        try:
            invitation = Invitations.objects.get(token=self.kwargs["token"])
        except Invitations.DoesNotExist as exc:
            raise NotFound(INVALID_INVITATION_MESSAGE) from exc

        if (
            invitation.status == "PENDING"
            and timezone.now() >= invitation.expires_at
        ):
            invitation.status = "EXPIRED"
            invitation.save(update_fields=["status"])

        if invitation.status != "PENDING":
            raise NotFound(INVALID_INVITATION_MESSAGE)

        return invitation

    def post(self, request, *args, **kwargs):
        return submit_public_application(request, self.kwargs["token"])


class PublicInvitationApplicationView(generics.CreateAPIView):
    serializer_class = PublicBorrowerApplicationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_invitation"

    def create(self, request, *args, **kwargs):
        return submit_public_application(request, kwargs["token"])


@transaction.atomic
def submit_public_application(request, token):
    try:
        invitation = Invitations.objects.select_for_update().get(token=token)
    except Invitations.DoesNotExist:
        raise NotFound(INVALID_INVITATION_MESSAGE)

    if (
        invitation.status == "PENDING"
        and timezone.now() >= invitation.expires_at
    ):
        invitation.status = "EXPIRED"
        invitation.save(update_fields=["status"])

    if invitation.status != "PENDING":
        raise NotFound(INVALID_INVITATION_MESSAGE)

    serializer = PublicBorrowerApplicationSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    used_at = timezone.now()
    claimed = Invitations.objects.filter(
        pk=invitation.pk,
        status="PENDING",
        expires_at__gt=used_at,
    ).update(
        status="USED",
        used_at=used_at,
    )
    if claimed != 1:
        raise NotFound(INVALID_INVITATION_MESSAGE)

    borrower: Borrower = serializer.save(lender=invitation.lender)

    invitation.borrower = borrower
    invitation.save(update_fields=["borrower"])

    return Response(
        {
            "detail": "Votre demande a été enregistrée avec succès.",
            "borrower_id": borrower.pk,
        },
        status=status.HTTP_201_CREATED,
    )
