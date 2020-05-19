import typing
import os

import boto3


_ssm_cache = {}


def load_ssm_environment_variables():
    """For any environment variable with a name ending in "__SSM_KEY",
    fetches the SSM parameter value at the path provided by that variable's value
    and adds that parameter value to the current mapping of environment variables,
    with the new variable name constructed by removing the "__SSM_KEY" suffix`
    from the source variable.

    Example:
        - Given an SSM parameter with a path of ``/my-service/foo`` and a value of ``"some_secret"``
        - Given the following ``os.environ`` environment variable state before calling:
            ``{"FOO__SSM_KEY": "/my-service/foo"}``
        - Calling this function will modify ``os.environ`` to the following state:
            ``{"FOO__SSM_KEY": "/my-service/foo", "FOO": "some_secret"}``
    """
    new_environment_variable_keys_to_paths = {}

    for key in os.environ.keys():
        if isinstance(key, str) and key.endswith('__SSM_KEY'):
            # Example: `FOO__SSM_KEY -> FOO`
            env_var_name = key.rpartition('__SSM_KEY')[0]
            ssm_parameter_path = os.environ[key]

            # Example: {'FOO': '/my-service/foo', ...}
            new_environment_variable_keys_to_paths[env_var_name] = ssm_parameter_path

    if new_environment_variable_keys_to_paths:
        # Example: {'/my-service/foo': 'secret_value', ...}
        ssm_paths_to_values = bulk_get_ssm_parameter_values(
            new_environment_variable_keys_to_paths.values()
        )

        for key, parameter_path in new_environment_variable_keys_to_paths.items():
            # Example: `os.environ['FOO'] = 'secret_value'`
            os.environ[key] = ssm_paths_to_values[parameter_path]


def get_ssm_parameter_value(key: str, use_cache: bool = True) -> str:
    """Retrieves an SSM parameter value based on the given SSM key (path)
    and caches the result.

    If ``use_cache`` is ``True`` and the given ``key`` has already been retrieved
    from the SSM API, then the SSM API will not be called for that key.
    Setting the ``use_cache`` argument to ``False`` forces the cache to be refreshed
    for the given ``key``. The cache will always be updated whenever a value is retrieved
    from the SSM API, regardless of this argument's value.

    Args:
        key: The SSM parameter key (path) for which a value should be retrieved
        use_cache: (Optional) If ``True`` and the given ``key`` exists in the SSM cache,
            returns the cached value instead of retrieving the value from the SSM API.
            Otherwise, the SSM API will be called regardless of whether ``key`` is cached.

    Returns:
        str: The SSM parameter value for the given key
    """
    try:
        assert use_cache is True
        value = _ssm_cache[key]
    except (AssertionError, KeyError):
        parameter_response = boto3.client('ssm').get_parameter(Name=key, WithDecryption=True)
        value = parameter_response['Parameter']['Value']
        _ssm_cache[key] = value

    return value


def bulk_get_ssm_parameter_values(keys: typing.Iterable[str]) -> typing.Dict[str, str]:
    """Retrieves multiple values from AWS SSM stored under the given keys.

    .. note::

        The local SSM cache state is not considered before retrieving any value(s)
        from the SSM API. Therefore, calling this function will always result in a call
        to the SSM API. However, the cache will always be updated following retrieval
        of values from the SSM API.

    Examples:
        .. code-block:: python

            >>> bulk_get_ssm_parameter_values(['some_key', 'another_key'])
            {'some_key': 'some_value', 'another_key': 'another_value'}

    Args:
        keys: A list of keys to the desired values in SSM

    Returns:
        dict: A mapping of the given keys to their corresponding values in SSM
    """
    parameter_response = boto3.client('ssm').get_parameters(Names=list(keys), WithDecryption=True)
    ssm_params = {param['Name']: param['Value'] for param in parameter_response['Parameters']}
    _ssm_cache.update(ssm_params)
    return ssm_params
