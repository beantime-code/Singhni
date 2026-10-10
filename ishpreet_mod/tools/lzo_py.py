"""Pure-Python LZO decompressors for the three variants used in Anvil forges: lzo1x, lzo1c, lzo2a.

Means no Homebrew or compiler: the tools run on stock macOS python3. anvil_forge.py still prefers
liblzo2 when it is installed (much faster), and falls back to this module otherwise.

Ported from the LZO reference decompressors (lzo1x_d.ch, lzo1b_d.ch with config1c.h, lzo2a_d.ch).
LZO is Copyright (C) 1996-2017 Markus F.X.J. Oberhumer, GPL v2 or later; this port is under the same licence.
Fuzz-tested against liblzo2 2.10 in tools/test_lzo_py.py.
"""


class LZOError(ValueError):
    pass


def _copy(out, m, n):
    """Append n bytes starting at out[m] (may overlap the bytes being written)."""
    if m < 0:
        raise LZOError('lookbehind overrun')
    d = len(out) - m
    if d >= n:
        out += out[m:m + n]
    else:
        while n > 0:
            k = min(n, d)
            out += out[m:m + k]
            n -= k
            d += k  # the copied pattern can now be reused from further back


def lzo1x(src, out_len):
    out = bytearray()
    ip = 0
    n = len(src)

    def zero_run(ip, base):
        t = 0
        while src[ip] == 0:
            t += 255
            ip += 1
        return t + base + src[ip], ip + 1

    t = src[0]
    state = 'loop'
    if t > 17:
        ip = 1
        t -= 17
        if t < 4:
            state = 'match_next'
        else:
            out += src[ip:ip + t]
            ip += t
            state = 'first_literal'
    while True:
        if state == 'loop':
            t = src[ip]; ip += 1
            if t >= 16:
                state = 'match'
            else:
                if t == 0:
                    t, ip = zero_run(ip, 15)
                out += src[ip:ip + t + 3]
                ip += t + 3
                state = 'first_literal'
            continue
        if state == 'first_literal':
            t = src[ip]; ip += 1
            if t >= 16:
                state = 'match'
                continue
            m = len(out) - (1 + 0x0800) - (t >> 2) - (src[ip] << 2)
            ip += 1
            _copy(out, m, 3)
            state = 'match_done'
            continue
        if state == 'match':
            if t >= 64:
                m = len(out) - 1 - ((t >> 2) & 7) - (src[ip] << 3)
                ip += 1
                _copy(out, m, (t >> 5) + 1)
            elif t >= 32:
                t &= 31
                if t == 0:
                    t, ip = zero_run(ip, 31)
                m = len(out) - 1 - ((src[ip] | (src[ip + 1] << 8)) >> 2)
                ip += 2
                _copy(out, m, t + 2)
            elif t >= 16:
                m = len(out) - ((t & 8) << 11)
                t &= 7
                if t == 0:
                    t, ip = zero_run(ip, 7)
                m -= (src[ip] | (src[ip + 1] << 8)) >> 2
                ip += 2
                if m == len(out):
                    break  # end of stream
                _copy(out, m - 0x4000, t + 2)
            else:
                m = len(out) - 1 - (t >> 2) - (src[ip] << 2)
                ip += 1
                _copy(out, m, 2)
            state = 'match_done'
            continue
        if state == 'match_done':
            t = src[ip - 2] & 3
            if t == 0:
                state = 'loop'
                continue
            state = 'match_next'
            continue
        if state == 'match_next':
            out += src[ip:ip + t]
            ip += t
            t = src[ip]; ip += 1
            state = 'match'
            continue
    if ip != n:
        raise LZOError(f'lzo1x: {n - ip} input bytes left over')
    return _check(out, out_len)


def lzo1c(src, out_len):
    # LZO1C constants (config1c.h: R_BITS 5, M3O_BITS 6)
    R0MIN, R0FAST, M2_MARKER = 32, 280, 64
    out = bytearray()
    ip = 0
    n = len(src)
    while True:
        t = src[ip]; ip += 1
        lit = 0
        if t < R0MIN:  # literal run
            if t == 0:
                t = src[ip]; ip += 1
                if t >= R0FAST - R0MIN:  # long R0 run, then back to the main loop
                    t -= R0FAST - R0MIN
                    t = R0FAST if t == 0 else 256 << t
                    out += src[ip:ip + t]
                    ip += t
                    continue
                t += R0MIN
            lit = t
        while True:
            if lit:
                out += src[ip:ip + lit]
                ip += lit
                while True:  # after literals: R1 matches (3-byte match + 1 literal) until a match marker
                    t = src[ip]; ip += 1
                    if t >= R0MIN:
                        break
                    m = len(out) - 1 - (t | (src[ip] << 5))
                    ip += 1
                    _copy(out, m, 3)
                    out.append(src[ip]); ip += 1
            if t >= M2_MARKER:  # M2 match
                m = len(out) - 1 - ((t & 31) | (src[ip] << 5))
                ip += 1
                _copy(out, m, (t >> 5) + 1)
                break
            lit, ip, eof = _lzo1c_m3(src, ip, out, t)  # M3/M4 match, may carry trailing literals
            if eof:
                return _done(out, out_len, ip, n, 'lzo1c')
            if not lit:
                break


def _lzo1c_m3(src, ip, out, t):
    """M3/M4 match. Returns (trailing literal count, ip, eof)."""
    t &= 31
    if t == 0:  # M4: long length
        while src[ip] == 0:
            t += 255
            ip += 1
        t += 31 + src[ip]  # (M4_MIN_LEN - M3_MIN_LEN) = 35 - 4
        ip += 1
    m = len(out) - (src[ip] & 63) - (src[ip + 1] << 6)
    ip += 2
    if m == len(out):
        return 0, ip, True
    _copy(out, m, t + 3)
    return src[ip - 2] >> 6, ip, False


def lzo2a(src, out_len):
    out = bytearray()
    ip = 0
    n = len(src)
    b = 0
    k = 0
    while True:
        if k < 1:
            b |= src[ip] << k; ip += 1; k += 8
        if b & 1 == 0:
            b >>= 1; k -= 1
            out.append(src[ip]); ip += 1
            continue
        b >>= 1; k -= 1
        if k < 1:
            b |= src[ip] << k; ip += 1; k += 8
        if b & 1 == 0:
            b >>= 1; k -= 1
            if k < 2:
                b |= src[ip] << k; ip += 1; k += 8
            t = 2 + (b & 3)
            b >>= 2; k -= 2
            m = len(out) - 1 - src[ip]; ip += 1
            _copy(out, m, t)
            continue
        b >>= 1; k -= 1
        t = src[ip]
        m = len(out) - ((t & 31) | (src[ip + 1] << 5))
        ip += 2
        t >>= 5
        if t == 0:
            t = 9
            while src[ip] == 0:
                t += 255
                ip += 1
            t += src[ip]; ip += 1
        else:
            if m == len(out):
                return _done(out, out_len, ip, n, 'lzo2a')
            t += 2
        _copy(out, m, t)


def _done(out, out_len, ip, n, name):
    if ip != n:
        raise LZOError(f'{name}: {n - ip} input bytes left over')
    return _check(out, out_len)


def _check(out, out_len):
    if out_len is not None and len(out) != out_len:
        raise LZOError(f'decompressed {len(out)} bytes, expected {out_len}')
    return bytes(out)


DECODERS = {0: lzo1x, 1: lzo1x, 2: lzo2a, 5: lzo1c}


def decompress(mode, src, out_len):
    if mode not in DECODERS:
        raise LZOError(f'compression mode {mode} not supported')
    try:
        return DECODERS[mode](src, out_len)
    except IndexError:
        raise LZOError('input overrun (truncated or not this LZO variant)') from None
