from django.urls import path, include
from .views import BorrowerListView

urlpatterns = [
    path(
        "",
        BorrowerListView.as_view(),
        name="borrower-list",
    ),
]