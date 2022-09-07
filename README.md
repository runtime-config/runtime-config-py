runtime-config-py
=================

This library allows you to update project settings at runtime. In its basic use case, it is just a client for the
[server](https://github.com/aleksey925/runtime-config), but if necessary, you can implement your adapter for the
desired source and get settings from them.

runtime-config-py supports Python 3.8+.

Examples of using:

- Create feature flags to control which features are enabled for users. Feature flags are especially useful when the
service is based on a microservice architecture and the addition of a new feature affects multiple services.

- Quick response to problems in project infrastructure. For example, if one of consumers sends too many requests to
another service, and you need to reduce its performance.


Table of contents:

- [Installation](#installation)
- [Usage](#usage)
- [Backend](#backend)
- [Development](#development)
  - [Tests](#tests)
  - [Style code](#style-code)


# Installation

This project can be installed directly from git:

```
pip install git+https://github.com/aleksey925/runtime-config-py.git
```

# Usage

Let's see a simple example of using this library together with aiohttp.

```python
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
```

Before running this code, you need to run [server](https://github.com/aleksey925/runtime-config) from which this
library can take new values for your variables.
If you don't do this, nothing bad will not happen. You simply cannot change the value of the name variable at runtime :)

This library supports several ways to access variables. All of them are shown below:

```python
print(config.name)
print(config['name'])
print(config.get('name', default='Dima'))
```

# Backend

Currently, only 1 [backend](https://github.com/aleksey925/runtime-config) is supported. Later, support for other
backends, such as redis, will probably be added to the library, but this is not in the nearest plans.

If you need support for another settings storage source right now, you can write your own source. Implementing this is
very simple. You need to create a class that will be able to retrieve data from the desired source and will inherit
from `runtime_config.sources.runtime_config_server.BaseSource`.  After that, an instance of the class you created
must be passed to the `RuntimeConfig.create` method.

```python
your_source = YourSource(...)
config = await RuntimeConfig.create(..., source=your_source)
```


# Development

## Tests

Check the work of the library on several versions of Python at once using the command below:

```
make test
```

## Style code

For automatic code formatting and code verification, you need to use the command below:

```
make lint
```
