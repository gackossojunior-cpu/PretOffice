from django.urls import path
from .views import LoanApplicationListCreateView, LoanDecisionView

urlpatterns = [
    path("", LoanApplicationListCreateView.as_view(), name="loan-list-create"),
    path("<int:pk>/decision/", LoanDecisionView.as_view(), name="loan-decision"),
]