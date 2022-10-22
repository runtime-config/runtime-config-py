import uvicorn
from fastapi import APIRouter, FastAPI

from runtime_config import RuntimeConfig
from runtime_config import get_instance as get_config_inst
from runtime_config.sources import ConfigServerSrc

router = APIRouter()


@router.get("/")
async def hello():
    config = get_config_inst()
    return f'Hello world {config.name}!'


async def init() -> None:
    source = ConfigServerSrc(host='http://127.0.0.1:8080', service_name='hello_world')
    await RuntimeConfig.create(init_settings={'name': 'Alex'}, source=source)


async def shutdown() -> None:
    await get_config_inst().close()


app = FastAPI()
app.on_event("startup")(init)
app.on_event("shutdown")(shutdown)
app.include_router(router)
uvicorn.run(app, port=5000)
