from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError


def filter_list_queryset(
    queryset,
    query_params,
    query_filter_fields=None,
    ordering_fields=(),
    default_ordering=None,
):
    for parameter, lookup in (query_filter_fields or {}).items():
        value = query_params.get(parameter)
        if value is None or value == "":
            continue
        try:
            queryset = queryset.filter(**{lookup: value})
        except (DjangoValidationError, ValueError) as exc:
            raise ValidationError(
                {parameter: "La valeur du filtre est invalide."}
            ) from exc

    ordering = query_params.get("ordering")
    if ordering:
        fields = [field.strip() for field in ordering.split(",")]
        if any(field.lstrip("-") not in ordering_fields for field in fields):
            raise ValidationError(
                {"ordering": "Le champ de tri demandé n'est pas autorisé."}
            )
        queryset = queryset.order_by(*fields)
    elif default_ordering:
        queryset = queryset.order_by(*default_ordering)

    return queryset


def lender_scoped_queryset(queryset, user, lender_filter_fields=("lender",)):
    filters = {field: user for field in lender_filter_fields}
    return queryset.filter(**filters)


class LenderScopedQuerysetMixin:
    lender_filter_fields = ("lender",)

    def get_queryset(self):
        queryset = super().get_queryset()
        return lender_scoped_queryset(
            queryset,
            self.request.user,
            self.lender_filter_fields,
        )

    def filter_queryset(self, queryset):
        return filter_list_queryset(
            queryset,
            self.request.query_params,
            getattr(self, "query_filter_fields", {}),
            getattr(self, "ordering_fields", ()),
            getattr(self, "default_ordering", None),
        )
