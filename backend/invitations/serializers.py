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

    def get_invitation_url(self, obj):
        request = self.context.get("request")

        if request: 
            return request.build_absolute_uri(
                f"/api/invitations/public/{obj.token}/"
            )
            
        return f"/api/invitations/public/{obj.token}/"


class PublicInvitationSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitations
        fields = (
            "status",
            "expires_at",
            "is_valid",
        )