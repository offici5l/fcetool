# FCE Tool
**Firmware Content Extractor - Extract specific files from remote ROM.ZIP archives without downloading the complete ROM**

## Installation
```bash
pip install fcetool
```

## CLI Usage
```bash
fcetool <URL> <FILENAME>
```

## Usage in Python Code
```python
import asyncio
from firmware_content_extractor import extract_async

asyncio.run(extract_async("URL", "boot.img", "./output"))
```

## API Usage
```bash
curl https://offici5l-fcetool.hf.space/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "ROM_URL", "images": "boot.img"}'
```

## Telegram Usage
Type @fcetoolbot <ROM_URL> <IMAGE_NAME> in any chat

## Web Interface
https://offici5l.github.io/fcetool

[API/Telegram/Web Supported only!](https://github.com/offici5l/fcetool/blob/main/api%2Fapp.py#L37)

___

<div align="center">

[![View Code Wiki](https://www.gstatic.com/_/boq-sdlc-agents-ui/_/r/YUi5dj2UWvE.svg)](https://codewiki.google/github.com/offici5l/fce)

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)

</div>