import struct

class ZipParser:
    def __init__(self, client):
        self.client = client
        self.files = {}

    async def parse(self):
        file_size = await self.client.get_size()
        read_size = min(65536, file_size)
        tail = await self.client.fetch_range(file_size - read_size, file_size)
        
        eocd_pos = tail.rfind(b"PK\x05\x06")
        if eocd_pos == -1: raise Exception("Invalid ZIP format")
        
        eocd = tail[eocd_pos:]
        cd_size = struct.unpack("<I", eocd[12:16])[0]
        cd_offset = struct.unpack("<I", eocd[16:20])[0]

        if cd_offset == 0xFFFFFFFF:
            zip64_loc = tail.rfind(b"PK\x06\x07")
            if zip64_loc != -1:
                end64_pos = struct.unpack("<Q", tail[zip64_loc+8:zip64_loc+16])[0]
                end64_data = await self.client.fetch_range(end64_pos, end64_pos + 56)
                cd_size = struct.unpack("<Q", end64_data[40:48])[0]
                cd_offset = struct.unpack("<Q", end64_data[48:56])[0]

        cd_data = await self.client.fetch_range(cd_offset, cd_offset + cd_size)
        
        pos = 0
        while pos < len(cd_data):
            if cd_data[pos:pos+4] != b"PK\x01\x02": break
            header = cd_data[pos:pos+46]
            method = struct.unpack("<H", header[10:12])[0]
            name_len = struct.unpack("<H", header[28:30])[0]
            extra_len = struct.unpack("<H", header[30:32])[0]
            comment_len = struct.unpack("<H", header[32:34])[0]
            lh_offset = struct.unpack("<I", header[42:46])[0]
            c_size = struct.unpack("<I", header[20:24])[0]
            
            fname = cd_data[pos+46:pos+46+name_len].decode('utf-8', 'ignore')
            
            if lh_offset == 0xFFFFFFFF:
                extra = cd_data[pos+46+name_len : pos+46+name_len+extra_len]
                p = 0
                while p < len(extra):
                    hid, dsize = struct.unpack("<HH", extra[p:p+4])
                    if hid == 1:
                        if lh_offset == 0xFFFFFFFF and len(extra[p+4:p+4+dsize]) >= 8:
                            lh_offset = struct.unpack("<Q", extra[p+4+dsize-8:p+4+dsize])[0]
                        break
                    p += 4 + dsize

            self.files[fname] = {
                "method": method, 
                "comp_size": c_size, 
                "lh_offset": lh_offset
            }
            pos += 46 + name_len + extra_len + comment_len
        return self.files

    async def get_data_start(self, fname):
        info = self.files[fname]
        off = info['lh_offset']
        head = await self.client.fetch_range(off, off + 256)
        n_len = struct.unpack("<H", head[26:28])[0]
        x_len = struct.unpack("<H", head[28:30])[0]
        return off + 30 + n_len + x_len
