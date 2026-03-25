<div align="center">

<img src="logo.svg" width="64" height="64">

**Firmware Content Extractor**

**Extract specific files from remote ROM.ZIP archives without downloading the full ROM**

</div>

---

### Web Interface

**https://offici5l.github.io/fcetool**

---

### Telegram Bot
**https://t.me/fcetoolbot**

---

### API
```bash
curl https://offici5l-fcetool.hf.space/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "ROM_URL", "images": "boot.img"}'
```

---

> **⚠️ Note:** Web, Telegram, and API support `.img` files only.
> For other file types, use:

---

### CLI
```bash
pip install fcetool
fcetool <URL> <FILENAME>
```

---

### Python
```python
import asyncio
from firmware_content_extractor import extract_async

asyncio.run(extract_async("URL", "boot.img", "./output"))
```

---

<div align="center">

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>