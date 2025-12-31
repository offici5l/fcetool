# FCE Tool
**Firmware Content Extractor - Extract specific files from remote ROM.ZIP archives without downloading the complete ROM**

## Installation
```
pip install fcetool
```

## CLI Usage
```
fcetool <URL> <FILENAME>
```

## Usage in Python Code
```
import asyncio
from fcetool import extract_async

asyncio.run(extract_async("URL", "boot.img", "./output"))
```

<div align="center">

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)

</div>