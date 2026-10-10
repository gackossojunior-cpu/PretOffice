from django.urls import path, include

from .views import MyLenderProfileView

urlpatterns = [
    path("me/", MyLenderProfileView.as_view(), name="my-lender-profile"),
]