from aiohttp import web

from runtime_config import RuntimeConfig
from runtime_config.sources import RuntimeConfigServer


async def hello(request):
    name = request.app['config'].name
    return web.Response(text=f'Hello world {name}!')


async def init(application):
    source = RuntimeConfigServer(host='http://127.0.0.1:8080', service_name='hello_world')
    config = await RuntimeConfig.create(init_settings={'name': 'Alex'}, source=source)
    application['config'] = config


async def shutdown(application):
    await application['config'].close()


app = web.Application()
app.on_startup.append(init)
app.on_shutdown.append(shutdown)
app.add_routes([web.get('/', hello)])
web.run_app(app, port=5000)
