# JARVIS Vision Grounding

JARVIS now uses this order for GUI interaction:

1. Windows UI Automation
2. App-specific deterministic automation (PyCharm file navigation)
3. Optional local OmniParser structured grounding
4. GPT-5 mini Vision as the last fallback

This keeps direct operations fast and avoids sending simple file clicks through a vision model.

## Optional OmniParser

OmniParser is a separate model service, not a normal Python dependency. The official project parses screenshots into structured UI elements and bounding boxes. See:

https://github.com/microsoft/OmniParser

A lightweight HTTP wrapper can expose `/process_image`, for example:

https://github.com/addy999/omniparser-api

The JARVIS client expects:

```text
OMNIPARSER_URL=http://127.0.0.1:7860/process_image
```

Add that variable to `.env` only after the local server is running.

The server may require a CUDA-capable NVIDIA GPU and substantial RAM depending on the OmniParser build. Do not install its large model stack into the JARVIS virtual environment automatically.

## Behaviour without OmniParser

Nothing breaks if the parser is unavailable. JARVIS continues with UI Automation and then GPT-5 mini Vision.

## Recommended tests

```text
нажми на agent.py
нажми на memory.py
нажми на шестерню
```

For `agent.py` and `memory.py` in PyCharm, JARVIS uses PyCharm's file navigation instead of guessing pixels.
