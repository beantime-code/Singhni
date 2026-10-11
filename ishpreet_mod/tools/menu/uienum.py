"""Read-only decoders for the inventory menu data in Syndicate's DataPC.forge pack 114 (Game Bootstrap Settings).

UIEnumBinding (type 2E772CD8), e.g. 'WeaponType', 'InventoryItemCategory', 'AvatarGearUICategory':
    entries UIEnumBindingEntry (E338E193): u32 enum value, then an icon link (C122A938: 01 01 <u64 texture id>, or 03 =
    none) and a UIString (81A7045D: u32 string id, ffffffff = none) followed by a UTF-16 debug name.
InventoryItemSettings (type C69075AB), one per item: name and description UIStrings, then
    InventoryItemCategorization (09A23DA0): u32 category (2 = weapons), u32 subcategory.

Verified on the stock records (cloud copy of pack 114, 2026-10-10). Weapons subcategories in use:
    1 Kukri (23 items), 4 Brass knuckles (19), 5 Cane (23), 7 pistols, 9 throwing knives, 12 darts, 14 gauntlets.
    2 (medium blunt), 3 (heavy) and 6 (blunderbuss) only hold Unity templates (TPL_WM_MediumWeapon_Blunt..., TPL_WH_
    HeavyWeapon..., TPL_Blunderbuss...). The WeaponType binding still carries Unity icons for 2 Heavy
    (UIicon_Weapon_TwoHands_Map) and 3 Long (UIicon_Weapon_Long_Map); both textures ship in DataPC_extra.forge.

    python3 uienum.py RECORD.bin [...]          # decode bindings / items from raw records
"""
import os
import struct
import sys

T_BINDING = 0x2E772CD8
T_ITEM = 0xC69075AB
ENTRY = bytes.fromhex('93e138e3')
ICON = bytes.fromhex('c122a938')
STRING = bytes.fromhex('5d04a781')
CATEG = bytes.fromhex('a03da209')


def binding(r):
    """[(value, icon texture id or None, string id or None, debug name)] in file order"""
    out, j = [], r.find(ENTRY)
    while j >= 0:
        nxt = r.find(ENTRY, j + 4)
        end = nxt if nxt >= 0 else len(r)
        value = struct.unpack_from('<I', r, j + 4)[0]
        icon = None
        k = r.find(ICON, j, end)
        if k >= 0 and r[k + 4] == 1:
            icon = struct.unpack_from('<Q', r, k + 6)[0]
        sid, name = None, ''
        s = r.find(STRING, j, end)
        if s >= 0:
            sid = struct.unpack_from('<I', r, s + 4)[0]
            n = struct.unpack_from('<I', r, s + 8)[0]
            if 0 < n < 200:
                name = r[s + 12:s + 12 + 2 * n].decode('utf-16le', 'replace').rstrip('\x00')
            if sid == 0xFFFFFFFF:
                sid = None
        out.append((value, icon, sid, name))
        j = nxt
    return out


def item(r):
    """(name string id, description string id, category, subcategory) or None if the record has no categorization"""
    c = r.find(CATEG)
    if c < 0:
        return None
    s1 = r.find(STRING)
    s2 = r.find(STRING, s1 + 4) if s1 >= 0 else -1
    sid = [struct.unpack_from('<I', r, s + 4)[0] if 0 <= s < c else None for s in (s1, s2)]
    cat, sub = struct.unpack_from('<II', r, c + 4)
    return sid[0], sid[1], cat, sub


def set_subcategory(r, sub):
    """record bytes with the item's subcategory changed (same size)"""
    c = r.find(CATEG)
    if c < 0:
        raise ValueError('no InventoryItemCategorization in this record')
    out = bytearray(r)
    struct.pack_into('<I', out, c + 8, sub)
    return bytes(out)


def rec_name(r):
    """name of a record as stored in a datapack (acs_kit Pack.recs bytes): u32 type, u32, u32 length, name"""
    n = struct.unpack_from('<I', r, 8)[0] if len(r) > 12 else 0
    return r[12:12 + n].decode('latin-1') if 0 < n < 300 else ''


def rec_type(r):
    return struct.unpack_from('<I', r, 0)[0] if len(r) >= 4 else None


def menu_tables(recs):
    """From pack 114's records [(id, flags, bytes)]: the weapon-related bindings and every weapon item."""
    want = {'WeaponType', 'InventoryItemCategory', 'AvatarGearUICategory'}
    out = {'bindings': {}, 'weapons': []}
    for rid, _, r in recs:
        t, nm = rec_type(r), rec_name(r)
        if t == T_BINDING and nm in want:
            out['bindings'][nm] = [{'value': v, 'icon': i, 'string': s, 'name': n} for v, i, s, n in binding(r)]
        elif t == T_ITEM:
            it = item(r)
            if it and it[2] == 2:
                out['weapons'].append({'id': rid, 'name': nm, 'name_string': it[0], 'desc_string': it[1],
                                       'subcategory': it[3]})
    return out


def main(argv):
    for p in argv:
        r = open(p, 'rb').read()
        print('==', os.path.basename(p))
        it = item(r)
        if it:
            print(f'   item: name string {it[0]}, description {it[1]}, category {it[2]}, subcategory {it[3]}')
        for v, i, s, n in binding(r):
            print(f'   {v:3d}  icon {i if i is None else hex(i)}  string {s if s is None else hex(s)}  {n}')


if __name__ == '__main__':
    main(sys.argv[1:])
