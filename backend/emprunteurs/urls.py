from django.urls import path, include
from .views import BorrowerDetailView, BorrowerListView

urlpatterns = [
    path(
        "<int:pk>/",
        BorrowerDetailView.as_view(),
        name="borrower-detail",
    ),
    path(
        "",
        BorrowerListView.as_view(),
        name="borrower-list",
    ),
]