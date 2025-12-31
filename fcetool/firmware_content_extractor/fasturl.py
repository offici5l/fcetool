xiaomi = {
    "fast_domain": "bkt-sgp-miui-ota-update-alisgp.oss-ap-southeast-1.aliyuncs.com",
    "original_domains": [
        "ultimateota.d.miui.com",
        "superota.d.miui.com",
        "bigota.d.miui.com",
        "cdnorg.d.miui.com",
        "bn.d.miui.com",
        "hugeota.d.miui.com",
        "cdn-ota.azureedge.net",
        "airtel.bigota.d.miui.com",
    ]
}

COMPANY_DOMAINS = {"xiaomi": xiaomi}

def fasturl(url):
    for company, config in COMPANY_DOMAINS.items():
        for original in config["original_domains"]:
            if original in url:
                return url.replace(original, config["fast_domain"])
    
    return url  # ما تغير → رجّع الأصلي