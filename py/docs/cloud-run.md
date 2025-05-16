# Deploy with Cloud Run

You can easily deploy your Genkit app to Cloud Run.

For prerequisites and basic scaffolding see [Cloud Run - Python quickstart](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service#before-you-begin) documentation.

Once you have a simple Cloud Run app set up and ready to go, update the `requirements.txt` to add Genkit libraries. In this example we'll be using the Google GenAI plugin.

```
genkit
genkit-plugin-google-genai
```

Update you app code to use Genkit.

```python
import os

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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

Then proceeed with Cloud Run [deployment](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service#deploy) instructions.
