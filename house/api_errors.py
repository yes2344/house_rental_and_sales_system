from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    original_data = response.data
    if isinstance(original_data, dict) and 'detail' in original_data:
        message = str(original_data['detail'])
        details = {}
    else:
        message = 'Request validation failed.' if response.status_code == 400 else 'Request could not be completed.'
        details = original_data

    response.data = {
        'error': {
            'status_code': response.status_code,
            'message': message,
            'details': details,
        },
    }
    return response
