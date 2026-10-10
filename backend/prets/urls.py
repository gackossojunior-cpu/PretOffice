from django.urls import path
from .views import (
    LoanApplicationListCreateView,
    LoanCancellationView,
    LoanDecisionView,
    LoanDetailView,
    LoanInstallmentsView,
    LoanRepaymentsView,
)

urlpatterns = [
    path("", LoanApplicationListCreateView.as_view(), name="loan-list-create"),
    path("<int:pk>/decision/", LoanDecisionView.as_view(), name="loan-decision"),
    path("<int:pk>/installments/", LoanInstallmentsView.as_view(), name="loan-installments"),
    path("<int:pk>/repayments/", LoanRepaymentsView.as_view(), name="loan-repayments"),
    path("<int:pk>/cancel/", LoanCancellationView.as_view(), name="loan-cancel"),
    path("<int:pk>/", LoanDetailView.as_view(), name="loan-detail"),
]