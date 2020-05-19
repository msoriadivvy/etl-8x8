class HTTPError(Exception):
    status_code = NotImplemented
    description = NotImplemented


class HTTPNotFoundError(HTTPError):
    status_code = 404
    description = 'Resource not found'


class HTTPBadRequestError(HTTPError):
    status_code = 400
    description = 'Bad request due to missing or malformed parameters'


class ServerError(HTTPError):
    status_code = 500
    description = 'Internal Server Error'


class Unauthorized(HTTPError):
    status_code = 401
    description = 'Unauthorized'


class UnsupportedMediaType(HTTPError):
    status_code = 415
    description = 'Unsupported Media Type'


class QuerystringParameterError(HTTPBadRequestError):
    pass
