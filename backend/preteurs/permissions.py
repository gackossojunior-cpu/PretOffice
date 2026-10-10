from rest_framework.permissions import BasePermission

class IsLender(BasePermission):
    message = "Seuls les prêteurs peuvent accéder à cette ressource."

    def has_permission(self, request, view):
        return (
            request.user and request.user.is_authenticated and request.user.role == "LENDER"
        )


class HasLenderProfile(BasePermission):
    message = "Un profil prêteur est requis pour accéder à cette ressource."

    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated
            and user.role == "LENDER"
            and hasattr(user, "lender_profile")
        )