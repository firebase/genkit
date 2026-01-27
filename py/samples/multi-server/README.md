# Genkit multi-server sample

This sample shows how to run multiple servers using the Genkit Web server
manager.

### Monitoring and Running

For an enhanced development experience, use the provided `run.sh` script to start the sample with automatic reloading:

```bash
./run.sh
```

This script uses `watchmedo` to monitor changes in:
- `src/` (Python logic)
- `../../packages` (Genkit core)
- `../../plugins` (Genkit plugins)
- File patterns: `*.py`, `*.prompt`, `*.json`

Changes will automatically trigger a restart of the sample. You can also pass command-line arguments directly to the script, e.g., `./run.sh --some-flag`.

## Output

```text
2025-03-15 18:06:09 [debug    ] ✅ Event loop is using uvloop (recommended️)
2025-03-15 18:06:09 [info     ] Starting servers...
2025-03-15 18:06:09 [info     ] Registering server             name=flows ports=range(3400, 3410)
2025-03-15 18:06:09 [info     ] Registering server             name=hello ports=[3300]
2025-03-15 18:06:09 [info     ] Registering server             name=reflection ports=[3100]
2025-03-15 18:06:09 [info     ] Registering server             name=reflection-starlette ports=[3200]
2025-03-15 18:06:09 [info     ] Checking port                  config=ServerConfig(name=flows, version=1.0.0, port=3400, ports=range(3400, 3410), host=localhost, log_level=info) host=localhost port=3400
2025-03-15 18:06:09 [info     ] Port available                 config=ServerConfig(name=flows, version=1.0.0, port=3400, ports=range(3400, 3410), host=localhost, log_level=info) host=localhost port=3400
2025-03-15 18:06:09 [info     ] Server started                 config=ServerConfig(name=flows, version=1.0.0, port=3400, ports=range(3400, 3410), host=localhost, log_level=info)
2025-03-15 18:06:09 [info     ] Checking port                  config=ServerConfig(name=hello, version=1.0.0, port=3300, ports=[3300], host=localhost, log_level=info) host=localhost port=3300
2025-03-15 18:06:09 [info     ] Port available                 config=ServerConfig(name=hello, version=1.0.0, port=3300, ports=[3300], host=localhost, log_level=info) host=localhost port=3300
2025-03-15 18:06:09 [info     ] Server started                 config=ServerConfig(name=hello, version=1.0.0, port=3300, ports=[3300], host=localhost, log_level=info)
2025-03-15 18:06:09 [info     ] Checking port                  config=ServerConfig(name=reflection, version=1.0.0, port=3100, ports=[3100], host=localhost, log_level=info) host=localhost port=3100
2025-03-15 18:06:09 [info     ] Port available                 config=ServerConfig(name=reflection, version=1.0.0, port=3100, ports=[3100], host=localhost, log_level=info) host=localhost port=3100
2025-03-15 18:06:09 [info     ] Server started                 config=ServerConfig(name=reflection, version=1.0.0, port=3100, ports=[3100], host=localhost, log_level=info)
2025-03-15 18:06:09 [info     ] Checking port                  config=ServerConfig(name=reflection-starlette, version=1.0.0, port=3200, ports=[3200], host=localhost, log_level=info) host=localhost port=3200
2025-03-15 18:06:09 [info     ] Port available                 config=ServerConfig(name=reflection-starlette, version=1.0.0, port=3200, ports=[3200], host=localhost, log_level=info) host=localhost port=3200
2025-03-15 18:06:09 [info     ] Server started                 config=ServerConfig(name=reflection-starlette, version=1.0.0, port=3200, ports=[3200], host=localhost, log_level=info)
2025-03-15 18:06:09 [info     ] Starting servers completed
```

## Stopping the sample

Lookup the process ID from [/\_\_serverz](http://localhost:3400/__serverz)

```bash
# SIGTERM
kill -15 ${PROCESS_ID}
```

## Testing This Demo

1. **Run the demo**:
   ```bash
   cd py/samples/multi-server
   ./run.sh
   ```

2. **Test the servers**:
   - [ ] Main API server at http://localhost:8000
   - [ ] Health check endpoint at /health
   - [ ] Server info endpoint at /info

3. **Expected behavior**:
   - Multiple servers start and run concurrently
   - Graceful shutdown handles all servers
   - Middleware and logging work across servers
