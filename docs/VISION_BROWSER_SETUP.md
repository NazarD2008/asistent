# Vision 2.0 + Browser Agent setup

## What JARVIS does now

Desktop click order:

1. Windows UI Automation
2. App-specific automation (for example, PyCharm file navigation)
3. Local OCR when the target is visible text
4. Optional OmniParser structured UI grounding
5. GPT Vision as the last resort

Browser order:

1. Direct browser URL/search tool when available
2. Playwright DOM automation for browser pages
3. Screen Vision only for browser UI that cannot be addressed structurally

## Install Python packages

```powershell
python -m pip install -r requirements.txt
```

Playwright uses the installed Google Chrome through `channel="chrome"`, so the project does not need Playwright's bundled Chromium for the normal JARVIS path.

## OCR

The Python OCR wrapper uses Tesseract if it is installed and visible in PATH.

Windows installer:

https://github.com/UB-Mannheim/tesseract/wiki

After installing, verify:

```powershell
tesseract --version
```

If `tesseract --version` works, JARVIS can use OCR automatically before OmniParser/Vision for text targets.

## OmniParser (optional)

OmniParser is optional and remains a separate local service because it requires model weights and its own inference environment.

When an OmniParser HTTP service is configured, JARVIS will prefer its structured element grounding before GPT Vision.

## Browser profile

Playwright uses a persistent profile under:

`%LOCALAPPDATA%\\Jarvis\\browser-profile`

This keeps browser cookies and sign-ins separate from the user's normal Chrome profile.

## Test commands

Desktop:

- `нажми на memory.py` in PyCharm
- `нажми на шестерню`
- `натисни на лупу`

Browser:

- `знайди на YouTube Minecraft`
- `пошукай на YouTube урок Python`
- `відкрий сторінку https://example.com`

For YouTube, JARVIS should use the DOM/browser agent rather than screen Vision.
