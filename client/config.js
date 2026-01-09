const SUPPORTED_FILES = ["boot.img","init_boot.img","dtbo.img","super_empty.img","vbmeta.img","vendor_boot.img","vendor_kernel_boot.img","preloader.img","recovery.img","logo.img","abl.img","hyp.img","modem.img","tz.img","xbl.img","lk.img","tee.img","md1img.img","preloader_emmc.img","preloader_raw.img","preloader_ufs.img","vbmeta_system.img","vbmeta_vendor.img","system_dlkm.img","vendor_dlkm.img","aop.img","aop_config.img","bluetooth.img","cpucp.img","cpucp_dtb.img","devcfg.img","dsp.img","featenabler.img","imagefv.img","keymaster.img","qupfw.img","shrm.img","uefi.img","uefisecapp.img","xbl_config.img","xbl_ramdump.img","scp.img","spmfw.img","sspm.img"];

const API_CONFIG = {
    baseUrl: 'https://offici5l-fcetool.hf.space',
    endpoints: {
        extract: '/extract'
    }
};
