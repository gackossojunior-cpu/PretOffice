from rest_framework.pagination import PageNumberPagination

from config.mixins import filter_list_queryset


class DefaultPagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def paginated_response(
    request,
    queryset,
    serializer_class,
    query_filter_fields=None,
    ordering_fields=(),
    default_ordering=None,
):
    queryset = filter_list_queryset(
        queryset,
        request.query_params,
        query_filter_fields,
        ordering_fields,
        default_ordering,
    )
    paginator = DefaultPagePagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(page, many=True)
    return paginator.get_paginated_response(serializer.data)
