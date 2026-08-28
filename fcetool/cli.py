import argparse
import asyncio
import os
import sys
import time
from .network import NetworkManager, SubFileClient
from .parser import ZipParser
from .direct import DirectExtractor
from .payload import PayloadExtractor
from .fasturl import fasturl

async def find_and_extract(client, parser, filename, out_path, p_name):

    files = parser.files
    real_file = next((f for f in files if f.split('/')[-1].lower() == filename.lower()), None)

    if real_file:
        extractor = DirectExtractor(client, parser)
        await extractor.extract(real_file, out_path)
        return True

    if "payload.bin" in files:
        extractor = PayloadExtractor(client, parser)
        try:
            await extractor.extract(p_name, out_path)
            return True
        except Exception as e:
            return False

    nested_zips = [
        f for f in files 
        if f.lower().endswith('.zip') and files[f]['method'] == 0
    ]

    for zip_name in nested_zips:
        data_start = await parser.get_data_start(zip_name)
        data_size = files[zip_name]['comp_size']
        sub_client = SubFileClient(client, data_start, data_size)
        sub_parser = ZipParser(sub_client)


        try:
            await sub_parser.parse()
            if await find_and_extract(sub_client, sub_parser, filename, out_path, p_name):
                return True
        except Exception as e:
            continue

    return False

async def extract_async(url, filename, out_dir="."):
    original_url = url
    try:
        if not url.startswith(('http://', 'https://')):
            return {
                "success": False,
                "error": "Invalid URL: Please provide a valid URL starting with http:// or https://",
                "url": original_url
            }
        url = fasturl(url)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        out_path = os.path.join(out_dir, filename)
        p_name = filename.replace(".img", "")

        async with NetworkManager(url) as client:
            parser = ZipParser(client)
            await parser.parse()

            success = await find_and_extract(client, parser, filename, out_path, p_name)

            if success:
                return {
                    "success": True,
                    "output_path": os.path.abspath(out_path),
                    "filename": filename
                }
            else:
                return {
                    "success": False,
                    "error": f"File '{filename}' not found in ROM (searched nested archives)"
                }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": original_url
        }

def interactive():
    url = input("URL of the ROM/ZIP: ").strip()
    filename = input("Target filename to extract (e.g. boot.img): ").strip()
    out_dir = input("Output dir (default: current directory '.'): ").strip() or "."
    return url, filename, out_dir

def main():
    parser = argparse.ArgumentParser(
        description="Firmware Content Extractor"
    )
    parser.add_argument("url", nargs="?", help="URL of the ROM/ZIP")
    parser.add_argument("filename", nargs="?", help="Target filename to extract")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=".",
        help="Output directory (default: current directory '.')"
    )

    args = parser.parse_args()

    if args.url is None or args.filename is None:
        url, filename, output_dir = interactive()
    else:
        url, filename, output_dir = args.url, args.filename, args.output_dir

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print(f"\n[INFO] Extracting '{filename}' from '{url}' into '{output_dir}'")

    start_time = time.perf_counter()

    result = asyncio.run(extract_async(url, filename, output_dir))
    elapsed = time.perf_counter() - start_time

    if result.get("success"):
        print(f"\n[OK] output: {filename} ({elapsed:.2f}s)\n")
    else:
        print(f"\n[FAIL] {result.get('error')} ({elapsed:.2f}s)\n")

if __name__ == "__main__":
    main()
