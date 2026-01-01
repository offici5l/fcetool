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
from fcetool import extract_async

asyncio.run(extract_async("URL", "boot.img", "./output"))
```

## API Usage
```bash
curl https://offici5l-fcetool.hf.space/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "ROM_URL", "images": "boot.img"}'
```
**API Supported images only:** `boot.img`, `init_boot.img`, `dtbo.img`, `super_empty.img`, `vbmeta.img`, `vendor_boot.img`, `vendor_kernel_boot.img`, `preloader.img`, `recovery.img`

## Telegram Usage
Type @fcetoolbot <ROM_URL> <IMAGE_NAME> in any chat

## Web Interface
https://offici5l.github.io/fcetool


<div align="center">

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)

</div>