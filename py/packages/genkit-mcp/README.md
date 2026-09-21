# Genkit MCP

Serves a Genkit app's own tools to [Model Context Protocol](https://modelcontextprotocol.io) clients
over stdio or streamable HTTP. A client half, which connects Genkit to an MCP server over stdio and
exposes that server's tools as Genkit `tool.v2` actions through a dynamic action provider, is under
development.

Under development: the package is not published yet. The client entry point below is the target
shape, landing with the client implementation.

Tracking issues: <https://github.com/genkit-ai/genkit/issues/6194> (client),
<https://github.com/genkit-ai/genkit/issues/6397> (server)

## Intended client usage

The example uses Gemini through `genkit-google-genai` and needs `GEMINI_API_KEY` set. Any model plugin works.

```python
import asyncio

from genkit import Genkit
from genkit_google_genai import GoogleAI
from genkit_mcp import define_mcp_client

ai = Genkit(plugins=[GoogleAI()], model=GoogleAI.gemini_model('gemini-flash-latest'))

client = define_mcp_client(
    ai,
    'everything',
    command='npx',
    args=['-y', '@modelcontextprotocol/server-everything'],
)


async def main() -> None:
    try:
        result = await ai.generate(prompt='Echo "hello".', tools=['everything:tool/*'])
        print(result.text)
    finally:
        await client.close()


asyncio.run(main())
```

## One server process per event loop

The client holds one connection, and so one server process, per event loop. While the Dev UI runs,
its reflection server has its own loop, so a second process starts for the same server. The two
processes do not share state, and servers that bind a port, take a lock file or own a browser profile
can clash.

## Serving your app as an MCP server

`create_mcp_server` wraps a `Genkit` instance and registers nothing, so the tools it serves are the
ones the app already has:

```python
import asyncio

from genkit import Genkit
from genkit_mcp import create_mcp_server
from pydantic import BaseModel

HOURS = {'saturday': '9am to 6pm', 'sunday': 'closed'}

ai = Genkit()


class Day(BaseModel):
    name: str


@ai.tool()
async def opening_hours(day: Day) -> str:
    """Report the shop's opening hours for a day of the week."""
    return HOURS.get(day.name.lower(), '10am to 7pm')


server = create_mcp_server(ai, 'bookshop', instructions='Ask about the shop.')

if __name__ == '__main__':
    asyncio.run(server.start())
```

The app's tools are read with `ai.list_tools()` on every `tools/list`, so a tool defined after the
server was built is still served. A tool whose input is not an object, such as a single scalar or an
optional model, is skipped: MCP arguments are always an object, and such a tool is not callable by
name either, rather than being listed and then failing. A model that refers to itself is served. An output schema is advertised only when it describes an object, since anything else
cannot be structured content. Tools a dynamic action provider supplies, from `define_mcp_client`
for instance, are not defined on the app and are not served.

A tool that raises answers with an error result. A `GenkitError` (including `PublicError`) sends its
status and message, without the text of its cause. Any other exception sends only `Tool '<name>'
failed`, since its text can carry a URL or a credential. The full error is logged on the server
either way, so raise a `GenkitError` for a failure the model should read and retry.

### stdio

`await server.start()` serves on this process's stdin and stdout until stdin closes. stdout is the
wire, so `start()` captures the real one for the transport and then points `sys.stdout` at stderr
for the rest of the process's life, because structlog's builtin default writes to stdout and one
stray line corrupts a JSON-RPC frame. A logging configuration your app chose for itself is left
alone, and a logger built before `start()` keeps the descriptor it captured. Pass
`redirect_stdout=False` to opt out.

`await server.serve(read_stream, write_stream)` serves on any SDK stream pair instead, and touches
nothing.

### Streamable HTTP

`server.asgi_app()` returns a Starlette app answering on `/mcp`, which uvicorn or any ASGI server
can serve as it is:

```python
app = server.asgi_app()  # uvicorn myserver:app
```

Pass `stateless=True` for a fresh transport per request with no session id, `json_response=True` for
one JSON body instead of an SSE stream, and `event_store=` to let a reconnecting client replay what
it missed. Nothing here touches stdout: only stdio makes stdout the wire.

The endpoint has no authentication. Anyone who can reach it can list and call every tool the app
defines, so bind it to localhost, which uvicorn does by default, or put authentication in front of
it before you bind it to a public interface. Mounting it in an app that already authenticates
requests is one way to do that.

A request whose `Host` header is not allowed gets a 421, and one from a browser whose `Origin` is not
allowed gets a 403. By default only localhost, `127.0.0.1` and `[::1]` on any port are allowed, so a
web page cannot reach a local server by rebinding its own name to `127.0.0.1`. Behind a proxy or on
a public name, list what clients will send:

```python
app = server.asgi_app(
    allowed_hosts=['tools.example.com'],
    allowed_origins=['https://app.example.com'],
)
```

In the default stateful mode, each session stays open until its client sends `DELETE` or the process
ends, and the MCP SDK reads a whole request body before it parses it. Neither has a limit here.
`stateless=True` keeps no sessions. Limit body size and request rate at a reverse proxy.

Starlette does not run a mounted app's lifespan, and the session manager inside needs one, so
mounting into an existing app means chaining it:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

mcp_app = server.asgi_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(app):
        yield


app = FastAPI(lifespan=lifespan)
app.mount('/api', mcp_app)  # the endpoint is then /api/mcp
```

## Known gaps

Scalar outputs and strings that look like JSON do not round-trip exactly. Clients join every text
block into the output, so a text content part is sent only beside no output or an object output, and
is dropped with a warning otherwise. A media part whose URL is not absolute is dropped with a
warning. A tool whose input is not an object is not served at all,
and an output schema that is not an object is not advertised, so a client is told less about such a
tool than Genkit knows. Nothing sends `notifications/tools/list_changed`; the list is re-read per
request instead. Progress, cancellation, sampling and elicitation are not supported. A
plugin-namespaced tool name carries a `/`, which the MCP SDK warns about. Whatever the app logs
before `start()` runs is on stdout, which that call is too late to have redirected. stdio reads and
writes UTF-8 whatever the locale, but is untested on Windows.
