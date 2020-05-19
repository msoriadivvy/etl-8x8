import os
import re

import aws_xray_sdk.core
import jwt
import sentry_sdk
from aws_xray_sdk.core import xray_recorder
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from common.aws_utils import api_gateway, ssm
from common.exceptions import QuerystringParameterError
from common.logging import setup_logger

logger = setup_logger(__name__)
sentry_sdk.init(dsn=os.environ['SENTRY_DSN'], integrations=[AwsLambdaIntegration()])
aws_xray_sdk.core.patch_all()


@xray_recorder.capture()
def authorize_for_authenticated_thor_token(event: dict, context: object) -> dict:
    """Produce an access policy corresponding to the requester's auth token.

    All policies produced by this authorizer apply to the entire API.

    Access is granted as long as the token provided in the request is a JWT
    issued by Thor and has not expired.

    See Also:
        https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html
    """
    authorized = False
    auth_token = re.match(r'Bearer\s+(.+)', event['authorizationToken']).groups()[0]
    secret_key = ssm.get_ssm_parameter_value(os.environ['THOR_API_SECRET_KEY__SSM_KEY'])
    try:
        jwt_payload = jwt.decode(auth_token, secret_key, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        principal_id = jwt.decode(auth_token, secret_key, algorithms=['HS256'], verify=False).get(
            'user_id', 'unknown_user'
        )
        context = {'message': 'Expired token'}
    except jwt.InvalidTokenError:
        principal_id = 'unknown_user'
        context = {'message': 'Invalid token'}
    else:
        authorized = True
        principal_id = jwt_payload['user_id']
        context = {'first_name': jwt_payload['first_name'], 'last_name': jwt_payload['last_name']}

    _, _, _, region, account_id, apigateway_arn = event['methodArn'].split(':')
    api_id, stage, *_ = apigateway_arn.split('/')
    return {
        'principalId': principal_id,
        'context': context,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow' if authorized else 'Deny',
                    'Resource': f'arn:aws:execute-api:{region}:{account_id}:{api_id}/{stage}/*',
                }
            ],
        },
    }


@xray_recorder.capture()
@api_gateway.format_errors
def get_greeting__http(event: dict, context: object) -> api_gateway.HTTPResponse:
    """Responds with a greeting, optionally tailored to a specified person

    :param event: The incoming API Gateway event
    :param context: The current Lambda context
    :return: A greeting response
    :raises HTTPBadRequestError: If the request specifies a numeric value
        for the ``person`` querystring parameter
    """
    greeting = {'phrase': 'Hello!', 'is_personalized': False}

    person = api_gateway.get_querystring_parameter(event, 'person')
    if person:
        if person.isnumeric():
            raise QuerystringParameterError('A number cannot be greeted')
        else:
            greeting['phrase'] = f'Hello, {person}!'
            greeting['is_personalized'] = True

    return api_gateway.HTTPResponse(status_code=200, body=greeting)
