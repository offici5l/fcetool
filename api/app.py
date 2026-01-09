import os
import time
import re
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from asyncio import Semaphore
import asyncio

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from huggingface_hub import HfApi
import requests
import firmware_content_extractor as fce

def get_real_ip(request: Request):
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0]
    return request.client.host

limiter = Limiter(key_func=get_real_ip)

app = FastAPI()

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

SUPPORTED_TARGETS = {"boot.img","init_boot.img","dtbo.img","super_empty.img","vbmeta.img","vendor_boot.img","vendor_kernel_boot.img","preloader.img","recovery.img","logo.img","abl.img","hyp.img","modem.img","tz.img","xbl.img","lk.img","tee.img","md1img.img","preloader_emmc.img","preloader_raw.img","preloader_ufs.img","vbmeta_system.img","vbmeta_vendor.img","system_dlkm.img","vendor_dlkm.img","aop.img","aop_config.img","bluetooth.img","cpucp.img","cpucp_dtb.img","devcfg.img","dsp.img","featenabler.img","imagefv.img","keymaster.img","qupfw.img","shrm.img","uefi.img","uefisecapp.img","xbl_config.img","xbl_ramdump.img","scp.img","spmfw.img","sspm.img"}

extraction_semaphore = Semaphore(4)

TEMP_DIR = "/tmp/extracted"
os.makedirs(TEMP_DIR, exist_ok=True)

HF_TOKEN = os.getenv("HF_TOKEN")
DATASET_REPO = "offici5l/fcetool"

if HF_TOKEN:
    hf_api = HfApi(token=HF_TOKEN)
else:
    hf_api = None

def sanitize_path(path: str) -> str:
    path = re.sub(r'[<>:"|?*]', '_', path)
    path = path.replace(' ', '_')
    return path

def generate_storage_path(url: str) -> str:
    parsed = urlparse(url)    
    domain = parsed.netloc
    path = parsed.path.lstrip('/')
    
    if path.endswith('.zip'):
        path = path[:-4]
    
    path = sanitize_path(path)
    domain = sanitize_path(domain)
    
    full_path = f"{domain}/{path}"
    return full_path

def check_file_in_dataset(storage_path: str, target: str) -> bool:
    if not hf_api:
        return False
    
    try:
        path_in_repo = f"{storage_path}/{target}"
        exists = hf_api.file_exists(
            repo_id=DATASET_REPO,
            filename=path_in_repo,
            repo_type="dataset"
        )
        return exists
    except Exception:
        try:
            url = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/main/{storage_path}/{target}"
            response = requests.get(url, stream=True, timeout=5)
            response.close()
            return response.status_code == 200
        except:
            return False

async def upload_to_dataset(file_path: str, storage_path: str, target: str) -> str:
    if not hf_api:
        raise Exception("HF_TOKEN not configured")
    
    path_in_repo = f"{storage_path}/{target}"
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: hf_api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=path_in_repo,
            repo_id=DATASET_REPO,
            repo_type="dataset",
            commit_message=f"Add {target} from {storage_path}"
        )
    )
    
    download_url = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/main/{path_in_repo}"
    return download_url

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "message": "Rate limit exceeded. Please try again later."
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Internal Server Error: {str(exc)}"
        }
    )

@app.post("/extract")
@limiter.limit("3/minute")
async def extract_target(request: Request, payload: dict):
    if extraction_semaphore.locked():
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "message": "Server is at full capacity. Please try again in 1-2 minutes."
            }
        )

    url = payload.get("url")
    target = payload.get("target")

    if not url or not target:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Missing 'url' or 'target' parameter in JSON body."
            }
        )

    if target not in SUPPORTED_TARGETS:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"Unsupported target type. Supported: {', '.join(SUPPORTED_TARGETS)}"
            }
        )

    start_time = time.time()
    storage_path = generate_storage_path(url)
    
    if hf_api and check_file_in_dataset(storage_path, target):
        cache_url = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/main/{storage_path}/{target}"
        return JSONResponse(
            status_code=200,
            content={
                "status": "cached",
                "message": "File already exists in dataset (from cache)",
                "download_url": cache_url,
                "target": target,
                "duration_seconds": int(time.time() - start_time)
            }
        )

    folder_name = storage_path.replace('/', '_')
    out_dir = os.path.join(TEMP_DIR, folder_name)
    raw_file_path = os.path.normpath(os.path.join(out_dir, target))

    os.makedirs(out_dir, exist_ok=True)
    
    try:
        async with extraction_semaphore:
            result = await fce.extract_async(url, target, out_dir)
        
        if result.get("success") and os.path.exists(raw_file_path):
            if hf_api:
                try:
                    download_url = await upload_to_dataset(raw_file_path, storage_path, target)
                    
                    os.remove(raw_file_path)
                    if os.path.exists(out_dir) and not os.listdir(out_dir):
                        os.rmdir(out_dir)
                    
                    end_time = time.time()
                    duration = int(end_time - start_time)

                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "completed",
                            "message": "Extraction completed and uploaded to dataset",
                            "download_url": download_url,
                            "target": target,
                            "duration_seconds": duration
                        }
                    )
                
                except Exception as upload_error:
                    if os.path.exists(raw_file_path):
                        os.remove(raw_file_path)
                    if os.path.exists(out_dir) and not os.listdir(out_dir):
                        os.rmdir(out_dir)
                    
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "failed",
                            "message": f"Upload to dataset failed: {str(upload_error)}",
                            "duration_seconds": int(time.time() - start_time)
                        }
                    )
            else:
                if os.path.exists(raw_file_path):
                    os.remove(raw_file_path)
                if os.path.exists(out_dir) and not os.listdir(out_dir):
                    os.rmdir(out_dir)
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "failed",
                        "message": "HF_TOKEN not configured. Cannot upload to dataset.",
                        "duration_seconds": int(time.time() - start_time)
                    }
                )
        else:
            if os.path.exists(out_dir) and not os.listdir(out_dir):
                os.rmdir(out_dir)
            
            return JSONResponse(
                status_code=400, 
                content={
                    "status": "failed", 
                    "message": result.get("error", "Extraction failed"),
                    "duration_seconds": int(time.time() - start_time)
                }
            )

    except Exception as e:
        if os.path.exists(out_dir) and not os.listdir(out_dir):
            os.rmdir(out_dir)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

@app.get("/files/{storage_path:path}/{target}")
async def get_file_info(storage_path: str, target: str):
    if check_file_in_dataset(storage_path, target):
        download_url = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/main/{storage_path}/{target}"
        return JSONResponse(
            status_code=200,
            content={
                "status": "exists",
                "message": "File found in dataset",
                "download_url": download_url,
                "target": target
            }
        )
    else:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "File not found in dataset"
            }
        )

@app.head("/health")
async def health_check():
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "message": "Service is healthy"
        }
    )

@app.get("/")
def home():
    hf_status = "enabled" if hf_api else "disabled"
    return JSONResponse(
        status_code=200,
        content={
            "status": "online",
            "message": "Service is running",
            "mode": "Direct-Upload-to-Dataset",
            "method": "POST /extract",
            "dataset": DATASET_REPO,
            "hf_integration": hf_status
        }
    )