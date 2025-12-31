import struct
import bz2
import lzma
import zstandard as zstd
import mmap
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PayloadExtractor:
    def __init__(self, client, parser):
        self.client = client
        self.parser = parser
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    @staticmethod
    def _read_varint(data, pos):
        res, shift = 0, 0
        while True:
            b = data[pos]
            pos += 1
            res |= (b & 0x7F) << shift
            if not (b & 0x80): return res, pos
            shift += 7

    def _parse_manifest(self, data, target):
        pos, end = 0, len(data)
        while pos < end:
            tag, pos = self._read_varint(data, pos)
            if (tag >> 3) == 13:
                length, pos = self._read_varint(data, pos)
                p_end = pos + length
                name = None
                ops = []
                cur = pos
                while cur < p_end:
                    ptag, cur = self._read_varint(data, cur)
                    pfield = ptag >> 3
                    if pfield == 1:
                        slen, cur = self._read_varint(data, cur)
                        name = data[cur:cur+slen].decode()
                        cur += slen
                    elif pfield == 8:
                        olen, cur = self._read_varint(data, cur)
                        ops.append(data[cur:cur+olen])
                        cur += olen
                    else:
                        wt = ptag & 7
                        if wt == 2:
                            slen, cur = self._read_varint(data, cur)
                            cur += slen
                        elif wt == 0:
                            _, cur = self._read_varint(data, cur)
                
                if name == target:
                    return [self._parse_op(op) for op in ops]
                pos = p_end
            else:
                wt = tag & 7
                if wt == 2:
                    l, pos = self._read_varint(data, pos)
                    pos += l
                elif wt == 0:
                    _, pos = self._read_varint(data, pos)
        return None

    def _parse_op(self, buf):
        pos, end = 0, len(buf)
        op = {'t': 0, 'off': 0, 'len': 0, 'dst': []}
        while pos < end:
            tag, pos = self._read_varint(buf, pos)
            fn = tag >> 3
            if fn == 1: op['t'], pos = self._read_varint(buf, pos)
            elif fn == 2: op['off'], pos = self._read_varint(buf, pos)
            elif fn == 3: op['len'], pos = self._read_varint(buf, pos)
            elif fn == 6:
                l, pos = self._read_varint(buf, pos)
                e_end = pos + l
                sb, nb = 0, 0
                while pos < e_end:
                    etag, pos = self._read_varint(buf, pos)
                    if (etag >> 3) == 1: sb, pos = self._read_varint(buf, pos)
                    elif (etag >> 3) == 2: nb, pos = self._read_varint(buf, pos)
                op['dst'].append((sb, nb))
            else:
                wt = tag & 7
                if wt == 2:
                    l, pos = self._read_varint(buf, pos)
                    pos += l
                elif wt == 0:
                    _, pos = self._read_varint(buf, pos)
        return op

    def _decompress(self, data, type_):
        if type_ == 1: return bz2.decompress(data)
        elif type_ == 8: return lzma.decompress(data)
        elif type_ == 14: return zstd.ZstdDecompressor().decompress(data)
        return data

    async def extract(self, partition, out_path):
        if "payload.bin" not in self.parser.files: raise Exception("payload.bin missing")
        
        info = self.parser.files["payload.bin"]
        offset = await self.parser.get_data_start("payload.bin")
        
        header = await self.client.fetch_range(offset, offset + 30)
        m_size = struct.unpack(">Q", header[12:20])[0]
        ms_size = struct.unpack(">I", header[20:24])[0]
        
        m_data = await self.client.fetch_range(offset+24, offset+24+m_size)
        ops = self._parse_manifest(m_data, partition)
        if not ops: raise Exception(f"Partition {partition} not found")
        
        base_off = offset + 24 + m_size + ms_size
        max_sz = max(((s+n)*4096 for op in ops for s,n in op['dst']), default=0)
        
        with open(out_path, "wb") as f: f.truncate(max_sz)
        fd = os.open(out_path, os.O_RDWR)
        mm = mmap.mmap(fd, max_sz)
        
        ops.sort(key=lambda x: x['off'])
        batches = []
        c_batch, b_start, b_end = [], -1, -1
        
        for op in ops:
            if not op['len']: continue
            s, e = op['off'], op['off'] + op['len']
            if not c_batch:
                c_batch, b_start, b_end = [op], s, e
            elif (s - b_end <= 1048576) and ((e - b_start) <= 33554432):
                c_batch.append(op)
                b_end = e
            else:
                batches.append((c_batch, b_start, b_end))
                c_batch, b_start, b_end = [op], s, e
        if c_batch: batches.append((c_batch, b_start, b_end))

        sem = asyncio.Semaphore(self.client.concurrency)
        
        async def worker(batch):
            ops_in, start, end = batch
            async with sem:
                raw = await self.client.fetch_range(base_off + start, base_off + end)
                mv = memoryview(raw)
                loop = asyncio.get_running_loop()
                for op in ops_in:
                    r_start = op['off'] - start
                    comp = mv[r_start : r_start + op['len']]
                    dec = await loop.run_in_executor(self.executor, self._decompress, comp, op['t'])
                    ptr = 0
                    for sb, nb in op['dst']:
                        sz = nb * 4096
                        mm[sb*4096 : sb*4096+sz] = dec[ptr:ptr+sz]
                        ptr += sz

        await asyncio.gather(*(worker(b) for b in batches))
        mm.close()
        os.close(fd)
        self.executor.shutdown()
