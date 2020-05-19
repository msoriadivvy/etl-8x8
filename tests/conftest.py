import contextlib
import os

import boto3
import jwt
import moto
import pytest
from aws_xray_sdk.core import xray_recorder


xray_recorder.configure(context_missing='LOG_ERROR')

os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
os.environ['THOR_API_SECRET_KEY__SSM_KEY'] = '/secret/key/param/name'
os.environ['SENTRY_DSN'] = ''


@pytest.fixture(scope='session')
def secret_key():
    return 'VERY_SECRET'


@pytest.fixture(scope='function', autouse=True)
def mock_aws_environment(secret_key):
    with contextlib.ExitStack() as stack:
        # fmt: off
        # Add AWS services to mock in every test...
        mock_aws_service_context_managers = (
            moto.mock_ssm(),
            moto.mock_dynamodb2(),
        )
        # fmt: on
        for service_mock in mock_aws_service_context_managers:
            stack.enter_context(service_mock)

        # Perform (mocked) AWS service calls to prepare the environment for each test...
        boto3.client('ssm').put_parameter(
            Name=os.environ['THOR_API_SECRET_KEY__SSM_KEY'], Type='SecureString', Value=secret_key
        )

        yield


@pytest.fixture(scope='session')
def auth_header(secret_key):
    token = jwt.encode({}, secret_key, algorithm='HS256').decode()
    return {'Authorization': f'Bearer {token}'}
