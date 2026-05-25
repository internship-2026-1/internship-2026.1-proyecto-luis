from rest_framework.response import Response


def build_response(*, success, message, data, status_code):
    return Response(
        {
            'success': success,
            'message': message,
            'data': data,
            'status': status_code,
        },
        status=status_code,
    )


def success_response(message, data=None, status_code=200):
    return build_response(
        success=True,
        message=message,
        data=[] if data is None else data,
        status_code=status_code,
    )


def error_response(message, data=None, status_code=400):
    return build_response(
        success=False,
        message=message,
        data=[] if data is None else data,
        status_code=status_code,
    )