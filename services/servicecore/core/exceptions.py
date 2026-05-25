from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.views import exception_handler

from .api_responses import error_response


def _normalize_error_data(value):
    if isinstance(value, ErrorDetail):
        return str(value)
    if isinstance(value, list):
        return [_normalize_error_data(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_error_data(item) for key, item in value.items()}
    return value


def _extract_message(data):
    if isinstance(data, dict):
        detail = data.get('detail')
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail:
            return str(detail[0])

        first_value = next(iter(data.values()), None)
        if isinstance(first_value, list) and first_value:
            return str(first_value[0])
        if isinstance(first_value, str):
            return first_value

    if isinstance(data, list) and data:
        return str(data[0])

    return 'Ha ocurrido un error.'


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    normalized_data = _normalize_error_data(response.data)
    return error_response(
        message=_extract_message(normalized_data),
        data=normalized_data,
        status_code=response.status_code or status.HTTP_400_BAD_REQUEST,
    )