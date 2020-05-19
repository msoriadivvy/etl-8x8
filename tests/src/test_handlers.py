import datetime
import json

import jwt
import pytest

from common import exceptions
from src import handlers


class TestAuthorizeForAuthenticatedThorToken:
    def test_produce_full_access_policy_for_valid_token(self, secret_key):
        """Validate that signed tokens result in a permissive access policy."""
        payload = {
            'exp': datetime.datetime.now() + datetime.timedelta(days=1),
            'iat': datetime.datetime.now(),
            'user_id': 1234,
            'first_name': 'Bob',
            'last_name': 'The Builder',
        }
        valid_jwt = jwt.encode(payload, secret_key).decode()

        event = {
            'type': 'TOKEN',
            'authorizationToken': f'Bearer {valid_jwt}',
            'methodArn': 'arn:aws:execute-api:us-west-2:1234:api_id/test/get/resource/subresource',
        }

        policy = handlers.authorize_for_authenticated_thor_token(event, None)
        expected_policy = {
            'principalId': 1234,
            'context': {'first_name': 'Bob', 'last_name': 'The Builder'},
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Allow',
                        'Resource': 'arn:aws:execute-api:us-west-2:1234:api_id/test/*',
                    }
                ],
            },
        }
        assert policy == expected_policy

    def test_raise_error_on_expired_token(self, secret_key):
        """Validate that expired tokens are rejected."""
        payload = {
            'exp': datetime.datetime(2000, 1, 1),
            'iat': datetime.datetime(2000, 1, 1),
            'user_id': 1234,
            'first_name': 'Sonic',
            'last_name': 'The Hedgehog',
        }
        expired_jwt = jwt.encode(payload, secret_key).decode()
        event = {
            'type': 'TOKEN',
            'authorizationToken': f'Bearer {expired_jwt}',
            'methodArn': 'arn:aws:execute-api:us-west-2:1234:api_id/test/get/resource/subresource',
        }

        policy = handlers.authorize_for_authenticated_thor_token(event, None)
        expected_policy = {
            'principalId': 1234,
            'context': {'message': 'Expired token'},
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Deny',
                        'Resource': 'arn:aws:execute-api:us-west-2:1234:api_id/test/*',
                    }
                ],
            },
        }
        assert policy == expected_policy

    def test_raise_error_on_invalid_token(self):
        """Validate that tokens signed with an unknown secret are rejected."""
        payload = {
            'exp': datetime.datetime(2000, 1, 1),
            'iat': datetime.datetime(2000, 1, 1),
            'user_id': 1234,
            'first_name': 'Kermit',
            'last_name': 'The Frog',
        }
        invalid_jwt = jwt.encode(payload, 'bad_secret_key').decode()
        event = {
            'type': 'TOKEN',
            'authorizationToken': f'Bearer {invalid_jwt}',
            'methodArn': 'arn:aws:execute-api:us-west-2:1234:api_id/test/get/resource/subresource',
        }
        policy = handlers.authorize_for_authenticated_thor_token(event, None)
        expected_policy = {
            'principalId': 'unknown_user',
            'context': {'message': 'Invalid token'},
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Deny',
                        'Resource': 'arn:aws:execute-api:us-west-2:1234:api_id/test/*',
                    }
                ],
            },
        }
        assert policy == expected_policy


@pytest.mark.parametrize(
    'invocation_event, expected_status_code, expected_response_body',
    (
        ({'queryStringParameters': None}, 200, {'phrase': 'Hello!', 'is_personalized': False}),
        (
            {'queryStringParameters': {'person': 'Joe'}},
            200,
            {'phrase': 'Hello, Joe!', 'is_personalized': True},
        ),
        (
            {'queryStringParameters': {'person': '11'}},
            400,
            {
                'description': exceptions.QuerystringParameterError.description,
                'error': 'A number cannot be greeted',
            },
        ),
    ),
)
def test_get_greeting__http(invocation_event, expected_status_code, expected_response_body):
    api_response = handlers.get_greeting__http(event=invocation_event, context=None)

    assert expected_status_code == int(api_response['statusCode'])
    assert expected_response_body == json.loads(api_response['body'])
