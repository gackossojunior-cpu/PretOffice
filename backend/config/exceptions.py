from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(response.data, dict) and "detail" in response.data:
        detail = str(response.data["detail"])
        errors = {}
    else:
        detail = "La requête n'a pas pu être traitée."
        errors = response.data

    response.data = {
        "detail": detail,
        "errors": errors,
    }
    return response
