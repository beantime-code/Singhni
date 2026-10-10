"""Decoders for Anvil AtomGraph files (the fight/animation state graph, NewDemo_DEV), Unity and Syndicate.

Verified on the user's files (2026-10-10): Syndicate DataPC_extra pack 6969 (52.8 MB) and Unity DataPC pack
'DataAI_GroupBehavior_Couple_TakeAway' (42.6 MB). Same file ID in both games (6426366647).
Serialized objects start with CRC32(class name) and are laid out in declaration order (see ACUFixes' ACU-RE
headers for the in-memory classes).

    rtcp(b)        -> runtime variables (graph variables): name, type, id = CRC32(name), data offset.
                      A condition's ValueToTestReferenceID is the INDEX into this list.
    conditions(b)  -> AtomCondition records: ref (variable index), type, operator, value (int at wrapper+12).
    clip_refs(b, ids) -> byte offsets of every animation reference (u64 file id) in the graph.
"""
import struct
import zlib

RTCP = struct.pack('<I', zlib.crc32(b'AtomRTCPDescriptor'))        # b3b3ca75
COND = struct.pack('<I', zlib.crc32(b'AtomCondition'))             # 76384757
WRAP = struct.pack('<I', zlib.crc32(b'AtomDataContainerWrapper'))  # b83d2231
OPS = ['==', '>', '>=', '<', '<=', '!=']
COND_TYPES = ['GRAPH_VARIABLE', 'MarkUp', 'GROUP', 'PLAYBACK_PERCENT', 'AccumulatedMarkUp']


def rtcp(b):
    """[{name, type, id, off, at}] in table order (index = condition reference)."""
    out, i = [], b.find(RTCP)
    while i != -1:
        n = struct.unpack_from('<I', b, i + 4)[0]
        if 0 < n < 100:
            name = b[i + 8:i + 8 + n]
            j = i + 8 + n + 1
            tl = struct.unpack_from('<I', b, j)[0]
            if 0 < tl < 40:
                tname = b[j + 4:j + 4 + tl]
                j += 4 + tl + 1
                rid, off = struct.unpack_from('<II', b, j)
                if rid == zlib.crc32(name):
                    out.append({'name': name.decode('latin1'), 'type': tname.decode('latin1'), 'id': rid,
                                'off': off, 'at': i})
        i = b.find(RTCP, i + 4)
    return out


def conditions(b):
    """[{at, ref, type, op, conj, dtype, val}]: ref = variable index for GRAPH_VARIABLE conditions."""
    out, i = [], b.find(COND)
    while i != -1:
        ref, markup, ctype, op, conj, query = struct.unpack_from('<IIIIII', b, i + 4)
        w = b.find(WRAP, i + 28, i + 80)
        if w != -1 and ctype < 5 and op < 6:
            dtype = struct.unpack_from('<I', b, w + 4)[0]
            val = struct.unpack_from('<i', b, w + 12)[0]
            out.append({'at': i, 'ref': ref, 'type': ctype, 'op': op, 'conj': conj, 'dtype': dtype, 'val': val})
        i = b.find(COND, i + 4)
    return out


def clip_refs(b, ids):
    """Sorted [(offset, id)] for every u64 in ids stored in b (any alignment). Needs numpy."""
    import numpy as np
    a8 = np.frombuffer(b, dtype=np.uint8)
    want = np.array(sorted(ids), dtype=np.uint64)
    out = []
    for a in range(8):
        n = (len(a8) - a) // 8
        v = a8[a:a + n * 8].view('<u8')
        for h in np.nonzero(np.isin(v, want))[0]:
            out.append((int(a + 8 * h), int(v[h])))
    return sorted(out)
