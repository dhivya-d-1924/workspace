from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Wraps every DRF error response in a consistent envelope:
    { "success": false, "error": { "code": ..., "message": ..., "details": ... } }
    """
    response = exception_handler(exc, context)

    if response is not None:
        details = response.data
        message = "Request failed."
        if isinstance(details, dict) and "detail" in details:
            message = str(details["detail"])
        elif isinstance(details, list) and details:
            message = str(details[0])

        response.data = {
            "success": False,
            "error": {
                "code": response.status_code,
                "message": message,
                "details": details,
            },
        }
    return response
