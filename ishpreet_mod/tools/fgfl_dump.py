"""Dump an AnvilToolkit Full File List (.fgfl) to a TSV of (forge, type-ish hash, name).

Source lists: https://github.com/Kamzik123/AnvilToolkit-Resources/tree/main/Full%20File%20Lists
Needs:  pip install pyooz   (open-source Oodle Kraken decoder)

    python3 fgfl_dump.py Syndicate.fgfl syn_names.tsv
    python3 fgfl_dump.py Unity.fgfl acu_names.tsv

Container: 'FGFL', u32 version, u32 flags, u32 ?, u32 decompressed size,
u32 compressed size, then one Oodle Kraken stream at offset 24.
The decompressed body is forge name, then data files and files as
NUL-terminated names with small binary headers between them. This script
only pulls the names (enough to answer "which forge holds X?"). For IDs, use
AnvilToolkit's own "Export FGFL" utility (Extra Utilities button).

The .refmap files (reference maps) are NOT decodable with pyooz. AnvilToolkit
reads them itself.
"""
import re
import struct
import sys

import ooz


def decompress(path):
    d = open(path, 'rb').read()
    if d[:4] != b'FGFL':
        sys.exit('not an FGFL file')
    _ver, _flags, _unk, dsz, _csz = struct.unpack('<5I', d[4:24])
    return ooz.decompress(d[24:], dsz)


def main(src, dst):
    d = decompress(src)
    forge = '?'
    last = None
    prev_end = 0
    with open(dst, 'w') as o:
        for m in re.finditer(rb'[\x20-\x7e]{3,}\x00', d):
            s = m.group()[:-1].decode()
            gap = d[prev_end:m.start()]
            prev_end = m.end()
            if s.startswith('DataPC') and s != last:
                forge = s
            if s == last:
                continue
            typ = gap[-12:-8].hex() if len(gap) >= 12 else ''
            o.write(f'{forge}\t{typ}\t{s}\n')
            last = s


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
