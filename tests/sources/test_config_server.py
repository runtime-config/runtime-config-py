import aiohttp
import pytest
from pytest_mock import MockerFixture

from runtime_config.entities.runtime_setting_server import Setting
from runtime_config.enums.setting_value_type import SettingValueType
from runtime_config.exceptions import ValidationError
from runtime_config.sources import ConfigServerSrc


class TestConfigServerSrc:
    async def test_get_settings(self, client_session_mock_factory):
        # arrange
        server_response = [
            {'name': 'timeout', 'value': '10', 'value_type': 'int', 'disable': False},
        ]
        client_session_mock = client_session_mock_factory(server_response)

        # act
        async with ConfigServerSrc(host='http://127.0.0.1', service_name='name') as inst:
            settings = await inst.get_settings()

        # assert
        assert settings == [Setting(name='timeout', value='10', value_type=SettingValueType.int, disable=False)]
        assert client_session_mock.close.call_count == 1

    @pytest.mark.parametrize('host', ['127.0.0.1', '127.0.0.1:8000', 'qwerty', '', None])
    async def test_get_settings__send_not_valid_host__raise_error(self, host):
        # act
        with pytest.raises(ValueError) as exc:
            ConfigServerSrc(host=host, service_name='name')

        # assert
        assert str(exc.value) == 'Invalid host url received'

    async def test_get_settings__server_return_unexpected_data__raise_error(self, client_session_mock_factory):
        # arrange
        server_response = [
            {'name': 'timeout', 'value': '10', 'value_type': 'qwerty', 'disable': False},
        ]
        client_session_mock_factory(server_response)

        # act & assert
        inst = ConfigServerSrc(host='http://127.0.0.1', service_name='name')
        with pytest.raises(ValidationError):
            await inst.get_settings()

    @pytest.fixture
    def client_session_mock_factory(self, mocker: MockerFixture):
        def factory(response):
            resp_mock = mocker.Mock()
            resp_mock.json = mocker.AsyncMock(return_value=response)
            client_session_mock = mocker.patch(
                'runtime_config.sources.config_server.aiohttp.ClientSession', spec=aiohttp.ClientSession
            )()
            client_session_mock.get = mocker.AsyncMock(return_value=resp_mock)

            return client_session_mock

        return factory
