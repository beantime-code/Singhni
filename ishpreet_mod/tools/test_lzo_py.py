"""Fuzz-test lzo_py against liblzo2 (Linux/macOS with liblzo2 installed).

    python3 test_lzo_py.py [rounds]
"""
import ctypes
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anvil_forge as af  # noqa: E402
import lzo_py  # noqa: E402

COMP = {1: ('lzo1x_1_compress', 1 << 22), 5: ('lzo1c_1_compress', 1 << 22), 2: ('lzo2a_999_compress', 1 << 22),
        15: ('lzo1x_999_compress', 1 << 22), 25: ('lzo1c_999_compress', 1 << 22)}


def compress(name, wrk, data):
    fn = getattr(af.lzo_lib(), name)
    fn.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
    out = ctypes.create_string_buffer(2 * len(data) + 1024)
    n = ctypes.c_size_t(0)
    assert fn(data, len(data), out, ctypes.byref(n), ctypes.create_string_buffer(wrk)) == 0
    return out.raw[:n.value]


def samples(rng):
    yield b''
    yield b'a'
    yield b'\0' * 70000
    yield os.urandom(65535)
    words = [b'xx_Fight_Sword', b'Atk', b'\0\0\0\0', b'\xff' * 7, b'Keyframe', b'0FA3067F', b'.', b'\x01\x02']
    for _ in range(rng):
        k = random.randint(1, 65535)
        mode = random.random()
        if mode < 0.3:
            d = bytes(random.getrandbits(8) for _ in range(min(k, 3000)))
        elif mode < 0.7:
            d = b''.join(random.choice(words) for _ in range(k // 6 + 1))[:k]
        else:
            base = os.urandom(random.randint(1, 300))
            d = (base * (k // len(base) + 1))[:k]
            d = bytearray(d)
            for _ in range(random.randint(0, 50)):
                d[random.randrange(len(d))] = random.getrandbits(8)
            d = bytes(d)
        yield d


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    random.seed(1234)
    count = 0
    for d in samples(rounds):
        for key, (name, wrk) in COMP.items():
            mode = {1: 1, 15: 1, 5: 5, 25: 5, 2: 2}[key]
            if not d and mode != 1:
                continue
            z = compress(name, wrk, d)
            got = lzo_py.decompress(mode, z, len(d))
            ref = af.decompress(mode, z, len(d)) if len(z) != len(d) else d
            assert got == d == ref, (name, len(d))
            count += 1
    print(f'ok: {count} streams decoded identically to liblzo2 (lzo1x, lzo1c, lzo2a)')


if __name__ == '__main__':
    main()
