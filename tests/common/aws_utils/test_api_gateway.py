import http
import json

import pytest

from common.aws_utils import api_gateway
from common import exceptions


class TestGetQuerystringParameterTestCase:
    def test_returns_named_parameter(self):
        assert 'bar' == api_gateway.get_querystring_parameter(
            {'queryStringParameters': {'foo': 'bar'}}, 'foo', default='buzz'
        )

    def test_returns_default_when_non_required_parameter_is_missing(self):
        assert 'buzz' == api_gateway.get_querystring_parameter(
            {'queryStringParameters': {}}, 'foo', default='buzz'
        )

    def test_raises_exception_when_required_parameter_is_missing_without_default(self):
        with pytest.raises(exceptions.QuerystringParameterError) as ctx:
            api_gateway.get_querystring_parameter(
                {'queryStringParameters': {}}, 'foo', required=True
            )

        assert str(ctx.value) == 'Missing required querystring parameter: foo'


class TestHTTPResponse:
    @pytest.mark.parametrize(
        'body_value, expected_serialized_body',
        (
            (None, 'null'),
            (api_gateway.NO_CONTENT, ''),
            (
                {'foo': 'bar', 'biz': ['b', 'a', 'z']},
                json.dumps({'foo': 'bar', 'biz': ['b', 'a', 'z']}),
            ),
            ('value', '"value"'),
        ),
        ids=(
            'None serialized to null',
            'NO_CONTENT serialized to empty string',
            'dict dumped to JSON object',
            'str dumped to JSON string',
        ),
    )
    def test_body_value_serialization(self, body_value, expected_serialized_body):
        response = api_gateway.HTTPResponse(status_code=200, body=body_value, extra_headers=None)

        assert response['body'] == expected_serialized_body

    @pytest.mark.parametrize(
        'extra_headers, expected_headers',
        (
            (
                None,
                {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True,
                    'Content-Type': 'application/json',
                },
            ),
            (
                {'X-Foo': 'bar'},
                {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True,
                    'Content-Type': 'application/json',
                    'X-Foo': 'bar',
                },
            ),
            (
                {'Content-Type': 'application/ld+json'},
                {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True,
                    'Content-Type': 'application/ld+json',
                },
            ),
        ),
        ids=('No extra headers', 'Adds X-Foo header', 'Replaces Content-Type header'),
    )
    def test_effective_headers(self, extra_headers, expected_headers):
        response = api_gateway.HTTPResponse(
            status_code=200, body=api_gateway.NO_CONTENT, extra_headers=extra_headers
        )

        assert response['headers'] == expected_headers

    @pytest.mark.parametrize('given_status_code', ('201', 201, http.HTTPStatus.CREATED))
    def test_formats_status_codes_as_str(self, given_status_code):
        response = api_gateway.HTTPResponse(status_code=given_status_code)

        assert response['statusCode'] == '201'


@pytest.mark.parametrize(
    'error_message, error_description, exception_cls, status_code',
    (
        ('Could not find it', 'Resource not found', exceptions.HTTPNotFoundError, '404'),
        (
            'Not a good request',
            'Bad request due to missing or malformed parameters',
            exceptions.HTTPBadRequestError,
            '400',
        ),
    ),
)
def test_format_errors(error_message, error_description, exception_cls, status_code):
    def _inner_function():
        if exception_cls:
            raise exception_cls(error_message)
        return error_message

    assert api_gateway.format_errors(_inner_function)() == {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
            'Content-Type': 'application/json',
        },
        'body': json.dumps({'description': error_description, 'error': error_message}),
    }


class TestFormatErrors:
    def _raise_an_error(self, exception_cls, message):
        raise exception_cls(message)

    @pytest.mark.parametrize(
        'error_message, error_description, exception_cls, status_code',
        (
            ('Could not find it', 'Resource not found', exceptions.HTTPNotFoundError, '404'),
            (
                'Not a good request',
                'Bad request due to missing or malformed parameters',
                exceptions.HTTPBadRequestError,
                '400',
            ),
        ),
    )
    def test_format_errors(self, error_message, error_description, exception_cls, status_code):
        decorated = api_gateway.format_errors(self._raise_an_error)

        assert decorated(exception_cls, error_message) == {
            'statusCode': status_code,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'description': error_description, 'error': error_message}),
        }

    def test_non_HTTPError_exceptions_are_unhandled(self):
        decorated = api_gateway.format_errors(self._raise_an_error)

        with pytest.raises(ValueError) as ctx:
            decorated(ValueError, 'Oh no!')

        assert str(ctx.value) == 'Oh no!'

    def test_return_values_outside_exception_context_are_unhandled(self):
        decorated = api_gateway.format_errors(lambda: 'A value')

        assert decorated() == 'A value'


class TestRequiresJSONPayload:
    def test_raise_error_on_deserialization_failure(self):
        decorated = api_gateway.requires_json_payload(lambda e, c: 'success!')

        with pytest.raises(exceptions.UnsupportedMediaType) as ctx:
            decorated({'body': '{not:json-!'}, None)

        assert str(ctx.value) == 'Request payload must be formatted JSON'

    def test_deserialize_json_payload(self):
        decorated = api_gateway.requires_json_payload(lambda e, c: e['body'])
        content = {'key': 'value'}
        processed_body = decorated({'body': json.dumps(content)}, None)
        assert processed_body == content
