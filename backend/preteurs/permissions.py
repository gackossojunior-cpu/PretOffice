from rest_framework.permissions import BasePermission

class IsLender(BasePermission):
    message = "Seuls les prêteurs peuvent accéder à cette ressource."

    def has_permission(self, request, view):
        return (
            request.user and request.user.is_authenticated and request.user.role == "LENDER"
        )