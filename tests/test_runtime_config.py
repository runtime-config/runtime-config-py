import os

import aiohttp
import pytest
from pytest_mock import MockerFixture

from runtime_config import RuntimeConfig, get_instance, sources
from runtime_config.entities.runtime_setting_server import Setting
from runtime_config.enums.setting_value_type import SettingValueType
from runtime_config.exceptions import InstanceNotFound, NotValidResponseError
from runtime_config.runtime_config import _instance


class TestRuntimeConfig:
    async def test_create__source_auto_initialization__success(self, mocker: MockerFixture, init_settings):
        # arrange
        host = '127.0.0.1'
        service_name = 'service_name'

        mocker.patch.dict(_instance, clear=True)
        mocker.patch.dict(os.environ, {'RUNTIME_CONFIG_HOST': host, 'RUNTIME_CONFIG_SERVICE_NAME': service_name})

        source_mock = mocker.patch(
            'runtime_config.runtime_config.sources.RuntimeConfigServer', spec=sources.RuntimeConfigServer
        )

        # act
        await RuntimeConfig.create(init_settings=init_settings)

        # assert
        source_mock.assert_called_with(host=host, service_name=service_name)

    async def test_create__source_auto_initialization_without_required_environment_vars__raise_exception(
        self, mocker: MockerFixture, init_settings
    ):
        # arrange
        mocker.patch.dict(_instance, clear=True)
        expected_error_msg = (
            'Define RUNTIME_CONFIG_HOST and RUNTIME_CONFIG_SERVICE_NAME environment variables or initialize '
            'source manually and pass it to create method.'
        )

        # act
        with pytest.raises(ValueError) as exc:
            await RuntimeConfig.create(init_settings=init_settings)

        # assert
        assert str(exc.value) == expected_error_msg

    async def test_create__creating_class_instance__automatically_received_settings_from_source(
        self, mocker: MockerFixture, init_settings, source_mock
    ):
        # arrange
        mocker.patch.dict(_instance, clear=True)
        source_mock.get_settings.return_value = [
            Setting(name='some_setting', value='123', value_type=SettingValueType.str, disable=False)
        ]

        # act
        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)

        # assert
        assert inst._settings == {'db_name': 'main', 'db_connect_timeout': 10, 'some_setting': '123'}

    @pytest.mark.parametrize(
        'setting_value, setting_value_type, after_convert',
        [
            ['123', SettingValueType.str, {'some_setting': '123'}],
            ['123', SettingValueType.int, {'some_setting': 123}],
            ['true', SettingValueType.bool, {'some_setting': True}],
            ['True', SettingValueType.bool, {'some_setting': True}],
            ['1', SettingValueType.bool, {'some_setting': True}],
            ['false', SettingValueType.bool, {'some_setting': False}],
            ['False', SettingValueType.bool, {'some_setting': False}],
            ['0', SettingValueType.bool, {'some_setting': False}],
            ['null', SettingValueType.null, {'some_setting': None}],
            ['None', SettingValueType.null, {'some_setting': None}],
            ['[1, 2, 3]', SettingValueType.json, {'some_setting': [1, 2, 3]}],
            ['{"key": "value"}', SettingValueType.json, {'some_setting': {"key": "value"}}],
        ],
    )
    async def test_refresh(
        self, mocker: MockerFixture, init_settings, source_mock, setting_value, setting_value_type, after_convert
    ):
        # arrange
        mocker.patch.dict(_instance, clear=True)

        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)
        source_mock.get_settings.return_value = [
            Setting(name='some_setting', value=setting_value, value_type=setting_value_type, disable=False)
        ]
        expected_settings = {'db_name': 'main', 'db_connect_timeout': 10}
        expected_settings.update(after_convert)

        # act
        await inst.refresh()

        # assert
        assert inst._settings == expected_settings

    async def test_refresh__update_inner_dict_in_settings__success(self, mocker: MockerFixture, source_mock):
        # arrange
        mocker.patch.dict(_instance, clear=True)

        init_settings = {
            'downloader': {
                'name': 'AsyncDownloader',
                'connection_params': {
                    'host': '127.0.0.1',
                    'port': 1234,
                    'credentials': {'simple': {'login': 'dima', 'password': '12345'}},
                },
            }
        }
        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)
        source_mock.get_settings.return_value = [
            Setting(
                name='downloader__connection_params__credentials__simple',
                value='{"login": "alex", "password": "qwerty"}',
                value_type=SettingValueType.json,
                disable=False,
            )
        ]
        expected_settings = {
            'downloader': {
                'name': 'AsyncDownloader',
                'connection_params': {
                    'host': '127.0.0.1',
                    'port': 1234,
                    'credentials': {'simple': {'login': 'alex', 'password': 'qwerty'}},
                },
            }
        }

        # act
        await inst.refresh()

        # assert
        assert inst._settings == expected_settings

    async def test_refresh__setting_value_cannot_be_converted_to_required_type__invalid_settings_skipped(
        self, mocker: MockerFixture, init_settings, source_mock
    ):
        # arrange
        mocker.patch.dict(_instance, clear=True)

        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)
        source_mock.get_settings.return_value = [
            Setting(name='invalid_setting', value='some_value', value_type=SettingValueType.bool, disable=False)
        ]

        # act
        await inst.refresh()

        # assert
        assert inst._settings == init_settings

    async def test_refresh__received_disabled_setting__disabled_settings_skipped(
        self, mocker: MockerFixture, init_settings, source_mock
    ):
        # arrange
        mocker.patch.dict(_instance, clear=True)

        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)
        source_mock.get_settings.return_value = [
            Setting(name='db_name', value='new_main', value_type=SettingValueType.int, disable=True)
        ]

        # act
        await inst.refresh()

        # assert
        assert inst._settings == init_settings

    async def test_refresh__server_returned_invalid_response__settings_have_not_been_updated(
        self, mocker: MockerFixture, init_settings, source_mock
    ):
        # arrange
        mocker.patch.dict(_instance, clear=True)

        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)
        source_mock.get_settings.side_effect = NotValidResponseError('error msg')

        # act
        await inst.refresh()

        # assert
        assert inst._settings == init_settings

    async def test_refresh__server_is_not_available__settings_have_not_been_updated(
        self, mocker: MockerFixture, init_settings, source_mock
    ):
        # arrange
        mocker.patch.dict(_instance, clear=True)

        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)
        source_mock.get_settings.side_effect = aiohttp.ClientConnectionError()

        # act
        await inst.refresh()

        # assert
        assert inst._settings == init_settings

    async def test_getitem(self, mocker: MockerFixture, source_mock):
        # arrange
        mocker.patch.dict(_instance, clear=True)
        init_settings = {
            'db': {
                'name': 'db_name',
                'port': 1234,
            },
            'icq': '15323534',
        }

        # act
        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)

        # assert
        assert inst['icq'] == '15323534'
        assert inst['db']['port'] == 1234

    async def test_getattr(self, mocker: MockerFixture, source_mock):
        # arrange
        mocker.patch.dict(_instance, clear=True)
        init_settings = {
            'db': {
                'name': 'db_name',
                'port': 1234,
            },
            'icq': '15323534',
        }

        # act
        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)

        # assert
        assert inst.icq == '15323534'
        assert inst.db['port'] == 1234

    async def test_close(self, mocker: MockerFixture, init_settings, source_mock):
        # arrange
        mocker.patch.dict(_instance, clear=True)
        inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)
        len_instance_before = len(_instance)

        # act
        await inst.close()

        # assert
        assert source_mock.close.call_count == 1
        assert len_instance_before == 1
        assert len(_instance) == 0


async def test_get_instance(mocker: MockerFixture, init_settings, source_mock):
    # arrange
    mocker.patch.dict(_instance, clear=True)
    expected_inst = await RuntimeConfig.create(init_settings=init_settings, source=source_mock)

    # act
    inst = get_instance()

    # assert
    assert expected_inst is inst


async def test_get_instance__runed_before_create_instance__raise_exception(
    mocker: MockerFixture, init_settings, source_mock
):
    # arrange
    mocker.patch.dict(_instance, clear=True)

    # act & assert
    with pytest.raises(InstanceNotFound):
        get_instance()


@pytest.fixture(name='init_settings')
def init_settings_fixture():
    return {
        "db_name": 'main',
        "db_connect_timeout": 10,
    }


@pytest.fixture(name='source_mock')
def source_mock_fixture(mocker: MockerFixture):
    source_mock = mocker.Mock(spec=sources.RuntimeConfigServer)
    source_mock.get_settings.return_value = []
    return source_mock
