"""Native (macOS/Linux) reader for AC Unity / Syndicate .forge files: no VM, no AnvilToolkit.

Lists the data files (packs) in a forge, decompresses them, and splits them into their files, so a Unity
DataPC.forge can be indexed and searched directly on the Mac.

No installs needed: stock python3 (3.8+). It uses liblzo2 if present (`brew install lzo`, ~10x faster),
otherwise the pure-Python decoders in lzo_py.py (fuzz-tested identical to liblzo2).

    python3 anvil_forge.py list    DataPC.forge [--grep Sword]          # packs: id, size, type, name
    python3 anvil_forge.py index   DataPC.forge out.csv [--grep Fight]  # every file in matching packs: ids, types, names
    python3 anvil_forge.py extract DataPC.forge OUTDIR --grep Fight_Sword [--files Sword_Atk]

Layout (format facts, written independently from public notes, e.g. ACExplorer's ACU reader):
  header: b'scimitar', 1 byte, int32 version (Unity 27), int64 offset A
  at A+36: int64 offset B. At B: int32 count, 4 pad, int64 index_table, int64 _, 8 pad, int64 name_table, int64 _
  index entry (20 B):  u64 data_offset, u64 pack_id, u32 data_size
  name entry (192 B):  u32 size, u64, u32, u32 pack_type, u64, 4*u32, char[128] name, 5*u32
  pack data: if it starts with MAGIC it is compressed, as one or two sections:
    MAGIC, 2 B, u8 compression (0/1 lzo1x, 2 lzo2a, 5 lzo1c), 3 B, u8 format
      format 128: u32 nblocks, nblocks*(u16 raw_size, u16 packed_size), then per block: u32 hash + packed bytes
      format 0:   u8 nblocks (=1), nblocks*(u32 packed_size, u32 raw_size), then per block: u32 hash + packed bytes
    format 128 has a second section (MAGIC again): section 1 = file table, section 2 = file data
  decompressed pack (format 128): u16 nfiles; nfiles*(u64 file_id, u32 size, u16 n_extra, n_extra*u16);
    then per file: u32 type, u32 size, u32 name_len, name, u8 flag (1 -> 3 B, u32 n, 12*n B), size bytes
"""
import argparse
import csv
import ctypes
import ctypes.util
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MAGIC = b'\x33\xAA\xFB\x57\x99\xFA\x04\x10'
LZO_FUNCS = {0: 'lzo1x_decompress_safe', 1: 'lzo1x_decompress_safe',
             2: 'lzo2a_decompress_safe', 5: 'lzo1c_decompress_safe'}

_lzo = None
_lzo_missing = False


def lzo_backend():
    """'liblzo2' or 'python'."""
    if os.environ.get('ANVIL_LZO') == 'python':
        return 'python'
    return 'liblzo2' if lzo_lib(required=False) else 'python'


def lzo_lib(required=True):
    global _lzo, _lzo_missing
    if _lzo is None and not _lzo_missing:
        cands = [ctypes.util.find_library('lzo2'), '/opt/homebrew/lib/liblzo2.dylib',
                 '/usr/local/lib/liblzo2.dylib', 'liblzo2.so.2']
        for c in cands:
            if not c:
                continue
            try:
                _lzo = ctypes.CDLL(c)
                break
            except OSError:
                pass
        if _lzo is None:
            _lzo_missing = True
            if required:
                sys.exit('LZO library not found: brew install lzo')
            return None
        for f in set(LZO_FUNCS.values()):
            fn = getattr(_lzo, f)
            fn.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p,
                           ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
            fn.restype = ctypes.c_int
    return _lzo


def decompress(mode, src, raw_len):
    if len(src) == raw_len:
        return src  # stored
    if mode not in LZO_FUNCS:
        raise ValueError(f'compression mode {mode} not supported')
    if os.environ.get('ANVIL_LZO') == 'python' or lzo_lib(required=False) is None:
        import lzo_py
        return lzo_py.decompress(mode, src, raw_len)
    dst = ctypes.create_string_buffer(raw_len)
    out_len = ctypes.c_size_t(raw_len)
    r = getattr(lzo_lib(), LZO_FUNCS[mode])(src, len(src), dst, ctypes.byref(out_len), None)
    if r != 0 or out_len.value != raw_len:
        raise ValueError(f'LZO mode {mode} failed (err {r}, {out_len.value}/{raw_len} bytes)')
    return dst.raw


class Reader:
    def __init__(self, b, pos=0):
        self.b, self.p = b, pos

    def take(self, n):
        v = self.b[self.p:self.p + n]
        if len(v) != n:
            raise EOFError
        self.p += n
        return v

    def s(self, fmt):
        n = struct.calcsize(fmt)
        return struct.unpack('<' + fmt, self.take(n))

    def left(self):
        return len(self.b) - self.p


LAST_SECTIONS = []  # (mode, format, nblocks) of the last pack read, for debugging


def read_section(r):
    """r is positioned just after MAGIC. Returns (format, [raw blocks]).

    Header: u16 container version, u8 compression mode, 3 bytes, u8 format.
    Format 128 block sizes are (raw, packed) pairs: u16 in container version 1 (Unity), u32 in version 2
    (Syndicate; confirmed on the user's DataPC_extra.forge). Format 0 is a run of block groups (u8 count,
    count*(u32 packed, u32 raw), then hash + data per block) until the pack ends (seen in Unity's
    PrefetchingFileInfos)."""
    cver, = r.s('H')
    mode, = r.s('B')
    r.take(3)
    fmt, = r.s('B')
    blocks = []
    if fmt == 128:
        n, = r.s('I')
        sizes = [r.s('HH' if cver < 2 else 'II') for _ in range(n)]  # raw, packed
        for raw, packed in sizes:
            r.take(4)
            blocks.append(decompress(mode, r.take(packed), raw))
    elif fmt == 0:
        while r.left():
            n, = r.s('B')
            sizes = [r.s('II') for _ in range(n)]  # packed, raw
            for packed, raw in sizes:
                r.take(4)
                blocks.append(decompress(mode, r.take(packed), raw))
    else:
        raise ValueError(f'unknown section format {fmt} (container v{cver}, compression mode {mode})')
    LAST_SECTIONS.append((mode, fmt, len(blocks), cver))
    return fmt, blocks


class Forge:
    def __init__(self, path):
        self.path = path
        self.file_size = os.path.getsize(path)
        with open(path, 'rb') as f:
            head = f.read(64)
        self.diag = {'file_size': self.file_size, 'head_hex': head.hex()}
        if head[:8] != b'scimitar':
            raise ValueError(f'not a forge file (starts with {head[:8]!r})')
        self.version, off_a = struct.unpack_from('<iQ', head, 9)
        self.diag.update(version=self.version, off_a=off_a)
        with open(path, 'rb') as f:
            f.seek(off_a)
            block_a = f.read(64)
            if len(block_a) < 44:
                raise ValueError(f'forge header points past the end of the file (offset {off_a}, file is '
                                 f'{self.file_size} bytes): truncated or corrupt forge, or version '
                                 f'{self.version} uses a different layout')
            off_b, = struct.unpack_from('<Q', block_a, 36)
            f.seek(off_b)
            block_b = f.read(48)
            if len(block_b) < 48:
                raise ValueError(f'pack table header points past the end of the file (offset {off_b}): '
                                 f'truncated or corrupt forge, or version {self.version} uses a different layout')
            count, pad, idx_off, nxt, unk2, name_off, unk3 = struct.unpack('<iiQqQQQ', block_b)
            self.diag.update(block_a_hex=block_a.hex(), off_b=off_b, block_b_hex=block_b.hex(), count=count,
                             idx_off=idx_off, name_off=name_off, unk=[pad, nxt, unk2, unk3])
            # The pack table is a chain of blocks: header (count, ?, index table, next block, ?, name table, ?).
            # All forges seen so far have one block (next = -1); further blocks are followed if present.
            blocks, seen = [], set()
            while True:
                if not (0 < count < 10_000_000) or idx_off >= self.file_size or name_off >= self.file_size:
                    raise ValueError(f'implausible pack table (count {count}, index @{idx_off}, names @{name_off}); '
                                     f'forge version {self.version} may use a different layout')
                f.seek(idx_off)
                idx = f.read(20 * count)
                f.seek(name_off)
                blocks.append((count, idx, f.read(192 * count)))
                seen.add(off_b)
                if nxt <= 0 or nxt >= self.file_size or nxt in seen:
                    break
                off_b = nxt
                f.seek(off_b)
                count, pad, idx_off, nxt, unk2, name_off, unk3 = struct.unpack('<iiQqQQQ', f.read(48))
            self.diag['blocks'] = len(blocks)
        self.packs = []
        bad_size = bad_off = total = 0
        for count, idx, names in blocks:
            for i in range(count):
                data_off, pack_id, size = struct.unpack_from('<QQI', idx, 20 * i)
                nsize, = struct.unpack_from('<I', names, 192 * i)
                ptype, = struct.unpack_from('<I', names, 192 * i + 16)
                name = names[192 * i + 44:192 * i + 172].split(b'\0', 1)[0].decode('utf-8', 'replace')
                bad_size += nsize != size
                bad_off += data_off + size > self.file_size
                self.packs.append({'id': pack_id, 'offset': data_off, 'size': size, 'type': ptype, 'name': name})
            total += count
        self.diag.update(size_mismatches=bad_size, out_of_file=bad_off)
        if total and (bad_size > total // 10 or bad_off > total // 10):
            raise ValueError(f'pack table looks wrong: {bad_size} size mismatches, {bad_off} entries past end of '
                             f'file out of {total}')

    def raw_pack(self, p):
        with open(self.path, 'rb') as f:
            f.seek(p['offset'])
            return f.read(p['size'])

    def pack_files(self, p):
        """Yield dicts (id, type, name, data) for the files inside pack p."""
        raw = self.raw_pack(p)
        del LAST_SECTIONS[:]
        if not raw.startswith(MAGIC):
            if MAGIC in raw:
                raise ValueError('compression marker in the middle of an uncompressed pack')
            body, fmt = raw, 128
        else:
            r = Reader(raw, 8)
            fmt, blocks = read_section(r)
            if fmt == 128:
                if r.take(8) != MAGIC:
                    raise ValueError('second compressed section missing')
                blocks += read_section(r)[1]
            if r.left():
                raise ValueError(f'{r.left()} trailing bytes after compressed data')
            body = b''.join(blocks)
        whole = {'id': p['id'], 'type': p['type'], 'name': p['name'], 'data': body}
        if fmt == 0:
            yield whole
            return
        try:
            files = self._split(body, p)
        except (EOFError, ValueError, struct.error):
            if raw.startswith(MAGIC):
                raise
            files = [whole]  # an uncompressed special pack (e.g. GlobalMetaFile) with no file table
        yield from files

    @staticmethod
    def _split(body, p):
        r = Reader(body)
        n, = r.s('H')
        table = []
        for _ in range(n):
            fid, size, extra = r.s('QIH')
            r.take(2 * extra)
            table.append(fid)
        files = []
        for fid in table:
            ftype, size, nlen = r.s('3I')
            name = r.take(nlen).decode('utf-8', 'replace') or f'{fid:016X}'
            flag, = r.s('B')
            if flag == 1:
                r.take(3)
                k, = r.s('I')
                r.take(12 * k)
            elif flag != 0:
                raise ValueError(f'unexpected flag {flag} in {p["name"]}')
            files.append({'id': fid, 'type': ftype, 'name': name, 'data': r.take(size)})
        return files


def block_checksum(stored):
    """Per-block checksum: Adler-32 seeded with 0, over the bytes as stored (confirmed on Syndicate blocks)."""
    import zlib
    return zlib.adler32(stored, 0) & 0xFFFFFFFF


def _section_spans(raw, pos):
    """Parse one compressed section at raw[pos] (MAGIC included). Returns (end, cver, mode, fmt, raw_sizes, data)."""
    r = Reader(raw, pos)
    if r.take(8) != MAGIC:
        raise ValueError(f'no section marker at {pos}')
    cver, = r.s('H')
    mode, = r.s('B')
    r.take(3)
    fmt, = r.s('B')
    if fmt != 128:
        raise ValueError('only format-128 packs can be rebuilt')
    n, = r.s('I')
    sizes = [r.s('HH' if cver < 2 else 'II') for _ in range(n)]
    out = []
    for raw_len, packed in sizes:
        r.take(4)
        out.append(decompress(mode, r.take(packed), raw_len))
    return r.p, cver, raw[pos:pos + 15], [s[0] for s in sizes], b''.join(out)


def _stored_section(cver, header, raw_sizes, data):
    """A format-128 section whose blocks are stored (packed size == raw size), with correct checksums.
    header = the original 15 header bytes (marker, version, mode, flags, format), copied unchanged."""
    if sum(raw_sizes) != len(data):
        raise ValueError('block sizes do not add up to the data length')
    fmt_sizes = '<HH' if cver < 2 else '<II'
    s = header + struct.pack('<I', len(raw_sizes))
    s += b''.join(struct.pack(fmt_sizes, n, n) for n in raw_sizes)
    pos = 0
    for n in raw_sizes:
        chunk = data[pos:pos + n]
        s += struct.pack('<I', block_checksum(chunk)) + chunk
        pos += n
    return s


def rebuild_pack(raw, replacements):
    """Return a new raw pack in which each {file_id: new_bytes} replaces that file's data.

    Safety rules: each replacement must have exactly the original file's length (so the file table, sizes and
    offsets stay identical); the file-table section is copied byte for byte; the data section is re-emitted as
    stored blocks with the original block boundaries and correct checksums. The result is verified by parsing it.
    """
    if not raw.startswith(MAGIC):
        raise ValueError('pack is not compressed: not supported')
    end1, cver, _, sizes1, table = _section_spans(raw, 0)
    end2, cver2, header2, sizes2, body = _section_spans(raw, end1)
    if end2 != len(raw):
        raise ValueError(f'{len(raw) - end2} trailing bytes after the data section')
    body = bytearray(body)
    r = Reader(table)
    n, = r.s('H')
    ids = []
    for _ in range(n):
        fid, size, extra = r.s('QIH')
        r.take(2 * extra)
        ids.append(fid)
    r = Reader(bytes(body))
    done = set()
    for fid in ids:
        ftype, size, nlen = r.s('3I')
        r.take(nlen)
        flag, = r.s('B')
        if flag == 1:
            r.take(3)
            k, = r.s('I')
            r.take(12 * k)
        start = r.p
        r.take(size)
        if fid in replacements:
            new = replacements[fid]
            if len(new) != size:
                raise ValueError(f'replacement for {fid} is {len(new)} bytes, the original is {size}')
            body[start:start + size] = new
            done.add(fid)
    missing = set(replacements) - done
    if missing:
        raise ValueError(f'file ids not in this pack: {sorted(missing)}')
    out = raw[:end1] + _stored_section(cver2, header2, sizes2, bytes(body))
    # verify: same table, replaced data where asked, everything else identical
    chk_end1, _, _, _, chk_table = _section_spans(out, 0)
    _, _, _, _, chk_body = _section_spans(out, chk_end1)
    if chk_table != table or chk_body != bytes(body):
        raise ValueError('verification of the rebuilt pack failed')
    return out


def _match(pat, s):
    return pat is None or re.search(pat, s, re.I)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('list'); a.add_argument('forge'); a.add_argument('--grep')
    a = sub.add_parser('index'); a.add_argument('forge'); a.add_argument('csv'); a.add_argument('--grep')
    a = sub.add_parser('extract'); a.add_argument('forge'); a.add_argument('outdir')
    a.add_argument('--grep', required=True, help='regex on pack name'); a.add_argument('--files', help='regex on file name')
    args = ap.parse_args(argv)
    fg = Forge(args.forge)
    packs = [p for p in fg.packs if _match(args.grep, p['name'])]
    if args.cmd == 'list':
        print(f'# forge version {fg.version}, {len(fg.packs)} packs, {len(packs)} matching')
        for p in packs:
            print(f"{p['id']}\t{p['size']}\t{p['type']:08X}\t{p['name']}")
    elif args.cmd == 'index':
        bad = 0
        with open(args.csv, 'w', newline='') as o:
            w = csv.writer(o)
            w.writerow(['forge', 'pack_id', 'pack_name', 'file_id', 'file_type', 'file_name', 'size'])
            for p in packs:
                try:
                    for f in fg.pack_files(p):
                        w.writerow([os.path.basename(args.forge), p['id'], p['name'], f['id'],
                                    f"{f['type']:08X}", f['name'], len(f['data'])])
                except Exception as e:
                    bad += 1
                    print(f"skip {p['name']}: {e}", file=sys.stderr)
        print(f'indexed {len(packs) - bad}/{len(packs)} packs -> {args.csv}')
    else:
        n = 0
        for p in packs:
            d = os.path.join(args.outdir, re.sub(r'[^\w.-]', '_', p['name']))
            for f in fg.pack_files(p):
                if not _match(args.files, f['name']):
                    continue
                os.makedirs(d, exist_ok=True)
                fn = f"{re.sub(r'[^\w.-]', '_', f['name'])}.{f['type']:08X}.{f['id']}.bin"
                with open(os.path.join(d, fn), 'wb') as o:
                    o.write(f['data'])
                n += 1
        print(f'wrote {n} files to {args.outdir}')


if __name__ == '__main__':
    main()
