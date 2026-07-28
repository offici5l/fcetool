<div align="center">

<img src="logo.png" width="64" height="64">

**Firmware Content Extractor**

**Extract specific files from remote firmware.ZIP archives without downloading the full firmware**

</div>

---

### Web Interface

> **⚠️ Note:** Supports all files except very large ones (like `system.img, system_ext.img, mi_ext.img, vendor.img, odm.img, product.img`) due to API resource limitations.
> If a file type is not supported yet, please open an issue to request its addition.
> For full support of all file types without limitations, use the [CLI](#cli).

**https://fcetool.github.io**

---

### CLI

**Installation**

```sh
pip install fcetool
```

**Usage**

```sh
fcetool <URL> <FILENAME> <OUTPUT_DIR>
```

- `URL`: URL of the ROM/ZIP
- `FILENAME`: Target filename to extract
- `OUTPUT_DIR` *(optional)*: Output directory (default: `.`)

---

<div align="center">

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>
