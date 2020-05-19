import collections
import os

import pytest

from common.aws_utils import ssm


@pytest.fixture(autouse=True)
def mock_boto3_clients(mocker):
    mocked_boto3_clients = collections.defaultdict(mocker.Mock)
    mocker.patch('boto3.client', new=lambda service: mocked_boto3_clients[service])
    return mocked_boto3_clients


@pytest.fixture()
def ssm_client(mock_boto3_clients):
    return mock_boto3_clients['ssm']


@pytest.fixture(autouse=True)
def mocked_ssm_parameters(mocker, ssm_client):
    parameter_map = {'/path/to/foo': 'something', '/path/to/bar': 'another'}

    def get_parameters(Names, WithDecryption):
        response = {'Parameters': []}
        for name in Names:
            if name in parameter_map.keys():
                response['Parameters'].append({'Name': name, 'Value': parameter_map[name]})
        return response

    def get_parameter(Name, WithDecryption):
        return {'Parameter': {'Value': parameter_map[Name]}}

    ssm_client.get_parameters = mocker.Mock(side_effect=get_parameters)
    ssm_client.get_parameter = mocker.Mock(side_effect=get_parameter)
    return parameter_map


class TestEnvironmentVariablePopulation:
    @pytest.fixture
    def initialize_environment_variables(self, monkeypatch):
        for k in list(filter(lambda key: key.endswith('__SSM_KEY'), os.environ.keys())):
            monkeypatch.delenv(k)

        monkeypatch.setenv('FOO__SSM_KEY', '/path/to/foo')
        monkeypatch.setenv('BAR__SSM_KEY', '/path/to/bar')
        monkeypatch.setenv('NOT_AN_SSM_KEY', 'does not change')

    def test_loads_ssm_derived_environment_variables(self, initialize_environment_variables):
        assert os.getenv('FOO') is None
        assert os.getenv('BAR') is None

        ssm.load_ssm_environment_variables()

        assert os.getenv('FOO') == 'something'
        assert os.getenv('BAR') == 'another'
        assert os.getenv('NOT_AN_SSM_KEY', 'does not change')

    def test_does_nothing_if_no_suffixed_environment_variables(self, monkeypatch):
        for k in list(filter(lambda key: key.endswith('__SSM_KEY'), os.environ.keys())):
            monkeypatch.delenv(k)
        assert not any(v.endswith('__SSM_KEY') for v in os.environ.keys())

        starting_env = os.environ.copy()

        ssm.load_ssm_environment_variables()

        assert os.environ == starting_env


class TestIndividualSSMParameterRetrieval:
    @pytest.fixture(autouse=True)
    def clear_cache_state(self, mocker):
        mocker.patch.dict(ssm._ssm_cache, {}, clear=True)

    def test_caches_retrieved_value_by_default(self, ssm_client):
        assert ssm.get_ssm_parameter_value('/path/to/foo') == 'something'
        assert ssm.get_ssm_parameter_value('/path/to/foo') == 'something'

        assert ssm_client.get_parameter.call_count == 1

    def test_can_force_fetch_for_cached_parameter(self, ssm_client):
        assert ssm.get_ssm_parameter_value('/path/to/foo') == 'something'
        assert ssm.get_ssm_parameter_value('/path/to/foo', use_cache=False) == 'something'

        assert ssm_client.get_parameter.call_count == 2
