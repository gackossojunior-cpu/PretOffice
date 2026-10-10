from django.urls import path 

from .views import InvitationListCreateView, PublicInvitationDetailView, PublicInvitationApplicationView

urlpatterns = [
    path("", InvitationListCreateView.as_view(), name="invitation-list-create",),
    path("public/<str:token>/", PublicInvitationDetailView.as_view(), name="public-invitation-detail",), 
    path("public/<str:token>/apply/", PublicInvitationApplicationView.as_view(), name="public-invitation-application",),
]