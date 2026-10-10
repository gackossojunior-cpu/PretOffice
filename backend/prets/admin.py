from django.contrib import admin

from .models import Installment, Loan, LoanApplication, Repayment


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "borrower", "lender", "amount_requested", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("borrower__first_name", "borrower__last_name", "lender__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "principal_amount", "status", "frequency", "disbursed_at")
    list_filter = ("status", "frequency", "interest_type")
    search_fields = ("application__borrower__first_name", "application__borrower__last_name")
    readonly_fields = tuple(field.name for field in Loan._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ("loan", "number", "due_date", "amount_due", "amount_paid", "status")
    list_filter = ("status", "due_date")
    readonly_fields = tuple(field.name for field in Installment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "loan", "amount", "payment_date", "payment_method", "created_at")
    list_filter = ("payment_method", "payment_date")
    readonly_fields = tuple(field.name for field in Repayment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
