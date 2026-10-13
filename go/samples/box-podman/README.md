# Genkit in a Box: podman

A shell tool runs in a podman (or docker) container while the model call and
the Gemini API key stay in the main process. The container side is a separate
entry, [`boxed/`](boxed/main.go); the runner cross-compiles it on the host for
the container's Linux VM, so this works from macOS with no Containerfile and
no Go toolchain in the image.

## Run

```bash
podman machine start          # macOS, once
export GEMINI_API_KEY=...
genkit start -- go run .
```

The first start builds `./boxed` and pulls `alpine:3`, which can take a moment.

Then call `runInBox` in the Dev UI:

| Input | Result |
| --- | --- |
| `{"cmd": "uname -sm"}` | `Linux aarch64` (or `x86_64`): a Linux container, even on a Mac |
| `{"cmd": "printenv GEMINI_API_KEY; echo demo=$BOX_DEMO"}` | no key, `demo=set by the host`: containers inherit nothing but `Env` |
| `{"cmd": "wget -T 3 -qO- https://example.com"}` | `bad address`: the internal network blocks egress |
| `{"cmd": "ls ~ /"}` | the container's own filesystem, plus this project dir |

Or ask `codingAgent` what it can find out about its machine.

Stray containers, if the process is killed without cleanup:

```bash
podman rm -f $(podman ps -aq --filter label=genkit-box)
```
