import functools
import http
import json
import typing

from common import exceptions
from common.logging import setup_logger


logger = setup_logger(__name__)

NO_CONTENT = type(
    'NO_CONTENT', (), {'__doc__': 'Singleton value representing an empty HTTP response body'}
)()


# fmt: off
def get_querystring_parameter(
    event: dict,
    parameter_name: str,
    required: bool = False,
    default: typing.Any = None
) -> str:
    """Helper function for retrieving a querystring parameter
    from a provided API Gateway invocation event

    Args:
        event: The API Gateway invocation event that provides incoming request data
        parameter_name: The name of the querystring parameter whose value should be retrieved
        required: If ``True`` and no querystring parameter matches the given ``parameter_name``,
            a :class:`~exceptions.QuerystringParameterError` exception will be raised.
            If ``False``, the provided ``default`` value will be returned when no matching
            querystring parameter can be found.
        default: The default value to return if no querystring parameter  matches
            the given ``parameter_name``.
            This argument has no effect if ``required`` is ``True``.

    Returns:
        str: The matched querystring parameter value, or the provided ``default`` value
            if no parameter was matched and ``required`` was ``False``

    Raises:
        exceptions.QuerystringParameterError: If ``required`` is ``True``
            and the provided ``event`` contained no querystring parameter
            matching the given ``parameter`` name.
    """
    #  fmt: on
    query_string_parameters = event['queryStringParameters'] or {}

    try:
        parameter_value = query_string_parameters[parameter_name]
    except KeyError:
        if required:
            raise exceptions.QuerystringParameterError(
                f'Missing required querystring parameter: {parameter_name}'
            )
        else:
            parameter_value = default

    return parameter_value


class HTTPResponse(dict):
    """Represents a JSON HTTP response suitable for returning from an API Gateway invocation"""

    def __init__(
        self,
        status_code: typing.Union[http.HTTPStatus, int] = http.HTTPStatus.OK,
        body=NO_CONTENT,
        extra_headers: typing.Optional[dict] = None,
    ):
        """Initializes a new HTTPResponse

        Args:
            status_code: HTTP response status code
            body: JSON-serializable value to use as the HTTP response body.
                If the :attr:`NO_CONTENT` singleton is provided, the response body will be empty.
                Defaults to :attr:`No_CONTENT`.
            extra_headers: Dictionary of extra HTTP headers to be included in the response
                or ``None`` if no extra headers should be added. Defaults to ``None``.
        """
        super().__init__()

        serialized_body = '' if body is NO_CONTENT else json.dumps(body)

        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
            'Content-Type': 'application/json',
        }
        if extra_headers:
            headers.update(extra_headers)

        self.update(
            {'statusCode': str(int(status_code)), 'headers': headers, 'body': serialized_body}
        )


def format_errors(fn: typing.Callable) -> typing.Callable:
    """Decorator for API Gateway handler functions that catches meaningful exceptions and formats
    error responses (as instances of :class:`HTTPResponse`) accordingly.

    Meaningful exceptions are defined and handled as-follows:
        - :class:`~exceptions.HTTPBadRequestError`:
            Results in a response with a ``400`` status code
        - :class:`~exceptions.HTTPNotFoundError`:
            Results in a response with a ``404`` status code
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except exceptions.HTTPError as e:
            logger.info(
                f'Issuing error response with status code {e.status_code}  '
                f'due to {type(e)} exception: {str(e)}'
            )
            return HTTPResponse(
                status_code=e.status_code, body={'description': e.description, 'error': str(e)}
            )

    return wrapper


def requires_json_payload(fn: typing.Callable) -> typing.Callable:
    """Decorator for API Gateway handler functions that deserializes JSON request payloads."""

    @functools.wraps(fn)
    def wrapper(event, context):
        try:
            event['body'] = json.loads(event.get('body'))
        except (json.JSONDecodeError, TypeError) as e:
            raise exceptions.UnsupportedMediaType('Request payload must be formatted JSON') from e
        return fn(event, context)

    return wrapper
