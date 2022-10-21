import pytest
from pytest_mock import MockerFixture

from runtime_config.libs.asyncio_utils import periodic_task


async def test_periodic_task(mocker: MockerFixture):
    # arrange
    callback_time = 10
    func_mock = mocker.AsyncMock(side_effect=Exception)
    sleep_mock = mocker.patch('runtime_config.libs.asyncio_utils.asyncio.sleep')

    # act
    with pytest.raises(Exception):
        await periodic_task(func=func_mock, callback_time=callback_time)

    # assert
    assert func_mock.call_count == 1
    sleep_mock.assert_called_with(callback_time)
