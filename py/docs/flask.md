# Build a Flask app

Prerequisites: make sure you have everything installed from [Get Started](./get-started.md) guide.


1. Install Genkit Flask plugin

    ```bash
    pip install git+https://github.com/firebase/genkit#subdirectory=py/plugins/flask
    ```

    Or create a `requirements.txt` file

    ```
    genkit-plugin-flask @ git+https://github.com/firebase/genkit#subdirectory=py/plugins/google-genai
    ```

1. Create `main.py` file:

    ```py
    from flask import Flask

    from genkit.ai import Genkit
    from genkit.plugins.flask import genkit_flask_handler
    from genkit.plugins.google_genai import (
        GoogleGenai,
        google_genai_name,
    )

    ai = Genkit(
        plugins=[GoogleGenai()],
        model=google_genai_name('gemini-2.0-flash'),
    )

    app = Flask(__name__)


    @app.post('/joke')
    @genkit_flask_handler(ai)
    @ai.flow()
    async def joke(name: str, ctx):
        return await ai.generate(
            on_chunk=ctx.send_chunk,
            prompt=f'tell a medium sized joke about {name}',
        )
    ```

1. Run the app:

    ```bash
    flask --app main.py run
    ```

    Or with Dev UI:

    ```bash
    genkit start -- flask --app main.py run
    ```

    You can invoke the flow via HTTP:

    ```bash
    curl -X POST http://127.0.0.1:5000/joke -d '{"data": "banana"}' -H 'content-Type: application/json' -H 'Accept: text/event-stream'
    ```

    or you can use [Genkit client library](https://js.api.genkit.dev/modules/genkit.beta_client.html).


## Authorization and custom context

You can do custom authorization and custom context parsing by passing a `ContextProvider` implementation.


```py
from genkit.types import GenkitError

async def my_context_provider(request):
    return {'username': parse_request_header(request.headers.get('authorization'))}

@app.post('/say_hi')
@genkit_flask_handler(ai, context_provider=my_context_provider)
@ai.flow()
async def say_hi(name: str, ctx):
    if not ctx.context.get('username'):
        raise GenkitError(status='UNAUTHENTICATED', message='user not provided')

    return await ai.generate(
        on_chunk=ctx.send_chunk,
        prompt=f'say hi to {ctx.context.get('username')}',
    )
```

`parse_request_header` can be your custom authorization header parsersing/validation.