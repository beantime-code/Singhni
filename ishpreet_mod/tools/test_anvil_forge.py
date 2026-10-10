"""Round-trip test for anvil_forge.py: builds a synthetic forge with lzo1x, lzo2a and lzo1c packs.

    python3 test_anvil_forge.py      (needs liblzo2, same as anvil_forge.py)

This checks the container parsing and all three decompressors. It does NOT prove the layout matches a real Unity
forge: run `anvil_forge.py list` on DataPC.forge for that (first real-file check, see INDEX).
"""
import ctypes
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anvil_forge as af  # noqa: E402

WORK = {'lzo1x_1_compress': 1 << 22, 'lzo2a_999_compress': 1 << 22, 'lzo1c_1_compress': 1 << 22}
COMP = {1: 'lzo1x_1_compress', 2: 'lzo2a_999_compress', 5: 'lzo1c_1_compress'}


def compress(mode, data):
    lib = af.lzo_lib()
    fn = getattr(lib, COMP[mode])
    fn.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
    out = ctypes.create_string_buffer(2 * len(data) + 1024)
    n = ctypes.c_size_t(0)
    wrk = ctypes.create_string_buffer(WORK[COMP[mode]])
    assert fn(data, len(data), out, ctypes.byref(n), wrk) == 0
    return out.raw[:n.value]


def section(mode, payload, block=0x8000, cver=1):
    """cver 1 = Unity (u16 block sizes), 2 = Syndicate (u32 block sizes)."""
    chunks = [payload[i:i + block] for i in range(0, len(payload), block)] or [b'']
    packed = []
    for c in chunks:
        z = compress(mode, c)
        packed.append(z if len(z) < len(c) else c)  # store raw when it doesn't shrink
    s = af.MAGIC + struct.pack('<H', cver) + bytes([mode]) + b'\0\0\0' + bytes([128]) + struct.pack('<I', len(chunks))
    s += b''.join(struct.pack('<HH' if cver < 2 else '<II', len(c), len(z)) for c, z in zip(chunks, packed))
    s += b''.join(b'HASH' + z for z in packed)
    return s


def pack_blob(mode, files, cver=1):
    table = struct.pack('<H', len(files))
    body = b''
    for fid, ftype, name, data in files:
        table += struct.pack('<QIH', fid, len(data) + 13 + len(name), 1) + b'\0\0'
        nb = name.encode()
        body += struct.pack('<3I', ftype, len(data), len(nb)) + nb + b'\0' + data
    return section(mode, table, cver=cver) + section(mode, body, cver=cver)


def build_forge(path, packs, cver=1):
    blobs = [pack_blob(m, files, cver) for _, _, m, files in packs]
    n = len(packs)
    hdr_a = 64
    off_b = 128
    idx_off = 256
    name_off = idx_off + 20 * n
    data_off = name_off + 192 * n
    buf = bytearray(data_off)
    buf[0:8] = b'scimitar'
    struct.pack_into('<iQ', buf, 9, 27, hdr_a)
    struct.pack_into('<Q', buf, hdr_a + 36, off_b)
    struct.pack_into('<iiQQQQQ', buf, off_b, n, 0, idx_off, 0, 0, name_off, 0)
    pos = data_off
    for i, ((pid, name, _, _), blob) in enumerate(zip(packs, blobs)):
        struct.pack_into('<QQI', buf, idx_off + 20 * i, pos, pid, len(blob))
        struct.pack_into('<I', buf, name_off + 192 * i, len(blob))
        struct.pack_into('<I', buf, name_off + 192 * i + 16, 0x0FA3067F)
        nb = name.encode()
        buf[name_off + 192 * i + 44:name_off + 192 * i + 44 + len(nb)] = nb
        pos += len(blob)
    with open(path, 'wb') as f:
        f.write(bytes(buf) + b''.join(blobs))


def main():
    rnd = os.urandom(5000)
    text = (b'xx_Fight_Sword_Atk_1m_Front_01 keyframes ' * 4000)
    packs = [
        (1001, 'xx_Fight_Sword_Combo_pack', 2, [(11, 0x0FA3067F, 'xx_Fight_Sword_Combo_01', text),
                                              (12, 0x0FA3067F, 'xx_Fight_Sword_Combo_02', rnd)]),
        (1002, 'xx_Fight_Sword_Kill_pack', 5, [(21, 0x0FA3067F, 'xx_Fight_Sword_Kill_Front_01_Atk', text[:70000]),
                                             (22, 0x0FA3067F, 'xx_Fight_Sword_Kill_Front_01_Dfn', text[:333])]),
        (1003, 'ACU_BaseSkeleton_Male', 1, [(31, 0x24AECB7C, 'ACU_BaseSkeleton_Male', text[:9999] + rnd)]),
    ]
    for cver in (1, 2):
        run(packs, cver)
    rebuild_test(packs)
    print('all good')


def rebuild_test(packs):
    """rebuild_pack: same-size replacement, everything else untouched, real checksums, wrong sizes refused."""
    import zlib
    with tempfile.TemporaryDirectory() as d:
        fp = os.path.join(d, 'T.forge')
        build_forge(fp, packs, 2)
        fg = af.Forge(fp)
        p = fg.packs[1]
        raw = fg.raw_pack(p)
        orig = list(fg.pack_files(p))
        new_data = bytes(reversed(orig[1]['data']))
        out = af.rebuild_pack(raw, {orig[1]['id']: new_data})
        r = af.Reader(out, 8)
        af.read_section(r)
        assert r.take(8) == af.MAGIC
        _, blocks = af.read_section(r)
        end1 = af._section_spans(out, 0)[0]  # every stored block carries Adler-32 (seed 0) of its bytes
        hdr = af.Reader(out, end1 + 15)
        nb, = hdr.s('I')
        sizes = [hdr.s('II') for _ in range(nb)]
        for raw_len, packed in sizes:
            ck, = hdr.s('I')
            assert ck == zlib.adler32(hdr.take(packed), 0) and raw_len == packed
        p2 = dict(p, offset=0, size=len(out))
        fg.raw_pack = lambda _p: out
        got = list(fg.pack_files(p2))
        assert [g['data'] for g in got] == [orig[0]['data'], new_data]
        assert [(g['id'], g['name']) for g in got] == [(o['id'], o['name']) for o in orig]
        try:
            af.rebuild_pack(raw, {orig[1]['id']: new_data + b'x'})
            raise AssertionError('size change was accepted')
        except ValueError:
            pass
    print('ok  rebuild_pack: same-size replacement, checksums, size guard')


def run(packs, cver):
    with tempfile.TemporaryDirectory() as d:
        fp = os.path.join(d, 'Test.forge')
        build_forge(fp, packs, cver)
        fg = af.Forge(fp)
        assert fg.version == 27 and [p['name'] for p in fg.packs] == [p[1] for p in packs]
        for p, (_, _, mode, files) in zip(fg.packs, packs):
            got = list(fg.pack_files(p))
            assert [(g['id'], g['type'], g['name'], g['data']) for g in got] == files, (p['name'], mode)
            print(f"ok  v{cver} mode {mode}  {p['name']}: {len(got)} files, {sum(len(g['data']) for g in got)} bytes")
        af.main(['index', fp, os.path.join(d, 'i.csv'), '--grep', 'Sword'])
        rows = open(os.path.join(d, 'i.csv')).read().splitlines()
        assert len(rows) == 5, rows
        af.main(['extract', fp, os.path.join(d, 'out'), '--grep', 'Kill', '--files', '_Atk$'])
        out = os.listdir(os.path.join(d, 'out', 'xx_Fight_Sword_Kill_pack'))
        assert out == ['xx_Fight_Sword_Kill_Front_01_Atk.0FA3067F.21.bin'], out


if __name__ == '__main__':
    main()
