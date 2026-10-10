from django.conf import settings
from rest_framework import serializers

from .models import Invitations

class InvitationSerializer(serializers.ModelSerializer):
    invitation_url = serializers.SerializerMethodField()

    class Meta:
        model = Invitations
        fields = (
            "id",
            "token",
            "status",
            "expires_at",
            "created_at",
            "used_at",
            "invitation_url",
        )

        read_only_fields = (
            "id",
            "token",
            "status",
            "expires_at",
            "created_at",
            "used_at",
            "invitation_url",
        )

    def get_invitation_url(self, obj) -> str:
        base_url = settings.INVITATION_PUBLIC_BASE_URL.rstrip("/")
        path = f"/api/invitations/public/{obj.token}/"

        if base_url:
            return f"{base_url}{path}"

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(path)
            
        return path


class PublicInvitationSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    lender_name = serializers.SerializerMethodField()

    class Meta:
        model = Invitations
        fields = (
            "is_valid",
            "lender_name",
        )

    def get_lender_name(self, obj) -> str:
        profile = getattr(obj.lender, "lender_profile", None)
        return (
            (profile.business_name if profile else "")
            or obj.lender.get_full_name()
            or obj.lender.username
        )


class InvitationRevokeResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()