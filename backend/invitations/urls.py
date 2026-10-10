from django.urls import path 

from .views import (
    InvitationDetailView,
    InvitationListCreateView,
    InvitationRevokeView,
    PublicInvitationApplicationView,
    PublicInvitationDetailView,
)

urlpatterns = [
    path("", InvitationListCreateView.as_view(), name="invitation-list-create",),
    path("<int:pk>/", InvitationDetailView.as_view(), name="invitation-detail",),
    path("<int:pk>/revoke/", InvitationRevokeView.as_view(), name="invitation-revoke",),
    path("public/<str:token>/", PublicInvitationDetailView.as_view(), name="public-invitation-detail",), 
    path("public/<str:token>/apply/", PublicInvitationApplicationView.as_view(), name="public-invitation-application",),
]