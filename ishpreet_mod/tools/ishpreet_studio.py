"""Ishpreet Studio: a local, browser-based front end for the forge tools. No VM, no Terminal, no installs.

Start it by double-clicking "Ishpreet Studio.command" (next to this folder), or: python3 ishpreet_studio.py
It serves http://127.0.0.1:<port>/?t=<token> to this Mac only, and opens your browser.

Everything it does is logged (with full tracebacks) to <output folder>/studio_log.txt and shown in the Debug
tab. "Bundle for Claude" packs the log, the forge header diagnostics and the small game files the cloud
session needs (skeletons, a few sword clips, the Aveline skirt pack) into one zip under 28 MB.
"""
import gzip
import hashlib
import io
import json
import os
import platform
import re
import secrets
import struct
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anvil_bones  # noqa: E402
import anvil_forge as af  # noqa: E402

VERSION = '1.2'
INDEX_VERSION = 2
TOKEN = secrets.token_urlsafe(16)
CONFIG_PATH = os.path.expanduser('~/.ishpreet_studio.json')
BUNDLE_LIMIT = 28 * 1024 * 1024
TYPE_NAMES = {0x0FA3067F: 'Animation', 0x24AECB7C: 'Skeleton', 0x415D9568: 'Mesh', 0x22ECBE63: 'BuildTable',
              0x95741049: 'Sub-Skeleton', 0x52E5AA85: 'ClothActionSettings', 0xA2B7E917: 'TextureMap'}

# --------------------------------------------------------------------------------------------- config + logging

DEFAULTS = {
    'unity_dir': '', 'syn_dir': '',
    'duleep_dir': os.path.expanduser('~/Downloads/Duleep_Files'),
    'out_dir': os.path.expanduser('~/Downloads/Duleep_Files/ishpreet_mod/out'),
}
CONFIG = dict(DEFAULTS)
LOG = []
LOG_LOCK = threading.Lock()


def load_config():
    try:
        CONFIG.update(json.load(open(CONFIG_PATH)))
    except (OSError, ValueError):
        pass


def save_config():
    with open(CONFIG_PATH, 'w') as f:
        json.dump(CONFIG, f, indent=1)


def out_dir():
    d = CONFIG['out_dir'] or DEFAULTS['out_dir']
    os.makedirs(d, exist_ok=True)
    return d


def log(level, msg):
    line = f"{time.strftime('%H:%M:%S')} {level:5} {msg}"
    with LOG_LOCK:
        LOG.append(line)
        try:
            with open(os.path.join(out_dir(), 'studio_log.txt'), 'a') as f:
                f.write(line + '\n')
        except OSError:
            pass
    print(line, flush=True)


# --------------------------------------------------------------------------------------------- game folders

BOTTLE_GLOBS = ['~/CXPBottles', '~/Library/Application Support/CrossOver/Bottles']
GAME_DIRS = {'unity': "Assassin's Creed Unity", 'syn': "Assassin's Creed Syndicate"}
# a forge that only that game has: identifies its folder whatever it is called
MARKERS = {'unity': 'DataPC_ACU_Paris.forge', 'syn': 'DataPC_ACVI_London.forge'}
SKIP_DIRS = {'windows', 'users', 'programdata', 'extracted', 'backups', 'dosdevices', '__pycache__', '.git'}


def _is_game_dir(game, d):
    try:
        return os.path.isfile(os.path.join(d, MARKERS[game]))
    except OSError:
        return False


def _walk_for(roots, max_depth=9):
    """Folders under roots holding a marker forge (depth-limited, skips system and AnvilToolkit output dirs)."""
    hits = {'unity': [], 'syn': []}
    for root in roots:
        root = os.path.expanduser(root)
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip('/').count('/')
        for dp, dns, fns in os.walk(root, followlinks=False):
            if dp.count('/') - base_depth >= max_depth:
                dns[:] = []
            dns[:] = [d for d in dns if d.lower() not in SKIP_DIRS]
            for game, marker in MARKERS.items():
                if marker in fns and dp not in hits[game]:
                    hits[game].append(dp)
    return hits


def _from_acs_kit():
    """Game folders named in Duleep_Files/acs_kit/*.py (the path settings the earlier sessions used)."""
    found = {'unity': [], 'syn': []}
    kit = os.path.join(CONFIG.get('duleep_dir') or DEFAULTS['duleep_dir'], 'acs_kit')
    if not os.path.isdir(kit):
        return found
    for fn in sorted(os.listdir(kit)):
        if not fn.endswith('.py'):
            continue
        try:
            text = open(os.path.join(kit, fn), encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for s in re.findall(r'''["']([^"'\n]*/[^"'\n]*)["']''', text):  # any quoted path
            p = os.path.abspath(os.path.expanduser(s))
            for cand in (p, os.path.dirname(p), os.path.dirname(os.path.dirname(p))):
                for game in ('unity', 'syn'):
                    if _is_game_dir(game, cand) and cand not in found[game]:
                        found[game].append(cand)
    return found


def detect():
    """Find the game folders: the usual launcher paths, then acs_kit's path settings, then a search of the
    CrossOver bottles for a forge only that game has."""
    found = {'unity_dir': [], 'syn_dir': []}
    t = time.time()
    for root in BOTTLE_GLOBS:
        root = os.path.expanduser(root)
        if not os.path.isdir(root):
            continue
        for bottle in sorted(os.listdir(root)):
            for base in ['drive_c/Program Files (x86)/Ubisoft/Ubisoft Game Launcher/games',
                         'drive_c/Program Files/Ubisoft/Ubisoft Game Launcher/games',
                         'drive_c/Program Files (x86)/Steam/steamapps/common',
                         'drive_c/Program Files/Steam/steamapps/common']:
                for key, name in GAME_DIRS.items():
                    p = os.path.join(root, bottle, base, name)
                    if os.path.isdir(p) and _is_game_dir(key, p):
                        found[f'{key}_dir'].append(p)
    # folder names vary ("Assassin s Creed Syndicate"): check every sibling of a found game folder for the marker
    for key in ('unity_dir', 'syn_dir'):
        for d in list(found['unity_dir'] + found['syn_dir']):
            parent = os.path.dirname(d)
            try:
                for n in sorted(os.listdir(parent)):
                    p = os.path.join(parent, n)
                    if os.path.isdir(p) and _is_game_dir(key[:-4], p) and p not in found[key]:
                        found[key].append(p)
            except OSError:
                pass
    if not found['unity_dir'] or not found['syn_dir']:
        for game, dirs in _from_acs_kit().items():
            found[f'{game}_dir'] += [d for d in dirs if d not in found[f'{game}_dir']]
    if not found['unity_dir'] or not found['syn_dir']:
        hits = _walk_for(BOTTLE_GLOBS + ['~/Games', '~/Downloads', '/Applications'])
        for game, dirs in hits.items():
            found[f'{game}_dir'] += [d for d in dirs if d not in found[f'{game}_dir']]
    log('info', f'detect ({time.time() - t:.1f}s): {json.dumps(found)}')
    return found


def game_dir(game):
    d = CONFIG.get(f'{game}_dir', '')
    if not d or not os.path.isdir(d):
        raise ValueError(f'{"Unity" if game == "unity" else "Syndicate"} folder not set or missing: {d!r} (Setup tab)')
    return d


def list_forges(game):
    """Forges in the game folder and one level down (Syndicate keeps its DLC forges in dlc_NN/ folders).
    Names are relative paths, e.g. 'dlc_14/DataPC_14_dlc.forge'."""
    d = game_dir(game)
    out = []
    for n in sorted(os.listdir(d)):
        p = os.path.join(d, n)
        if n.lower().endswith('.forge') and os.path.isfile(p):
            out.append({'name': n, 'size': os.path.getsize(p)})
        elif os.path.isdir(p) and n.lower() not in SKIP_DIRS:
            try:
                for m in sorted(os.listdir(p)):
                    q = os.path.join(p, m)
                    if m.lower().endswith('.forge') and os.path.isfile(q):
                        out.append({'name': f'{n}/{m}', 'size': os.path.getsize(q)})
            except OSError:
                pass
    return out


def forge_path(game, name):
    """Absolute path of a forge given its name from list_forges (no escaping the game folder)."""
    d = os.path.realpath(game_dir(game))
    path = os.path.realpath(os.path.join(d, name))
    if not path.startswith(d + os.sep):
        raise ValueError(f'forge {name!r} is outside the game folder')
    return path


def forge_names(game):
    """{basename.lower(): relative name} so plans can name a forge without its folder."""
    out = {}
    for f in list_forges(game):
        out.setdefault(os.path.basename(f['name']).lower(), f['name'])
    return out


_FORGES = {}


def forge(game, name):
    path = forge_path(game, name)
    key = (path, os.path.getmtime(path))
    if key not in _FORGES:
        t = time.time()
        _FORGES[key] = af.Forge(path)
        log('info', f'opened {name}: version {_FORGES[key].version}, {len(_FORGES[key].packs)} packs '
                    f'in {time.time() - t:.2f}s')
    return _FORGES[key]


def safe(s):
    return re.sub(r'[^\w.-]', '_', s)[:150]


# --------------------------------------------------------------------------------------------- actions

def act_env(_):
    return {'version': VERSION, 'python': sys.version.split()[0], 'platform': platform.platform(),
            'machine': platform.machine(), 'lzo': af.lzo_backend(), 'tools': HERE, 'config': CONFIG,
            'config_path': CONFIG_PATH}


def act_set_config(a):
    for k in DEFAULTS:
        if k in a:
            CONFIG[k] = os.path.expanduser(str(a[k]).strip())
    save_config()
    log('info', f'config saved: {json.dumps(CONFIG)}')
    warnings = [f"{'Unity' if g == 'unity' else 'Syndicate'} folder has no {MARKERS[g]}: is it the game folder?"
                for g in ('unity', 'syn') if not _is_game_dir(g, CONFIG.get(f'{g}_dir') or '')]
    for w in warnings:
        log('WARN', w)
    return dict(CONFIG, warnings=warnings)


def act_detect(_):
    return detect()


def act_selftest(_):
    """Decode the bundled synthetic forge with the active LZO backend and with pure Python."""
    exp = json.load(open(os.path.join(HERE, 'selftest', 'expected.json')))
    results = []
    for backend in ['active', 'python']:
        old = os.environ.get('ANVIL_LZO')
        if backend == 'python':
            os.environ['ANVIL_LZO'] = 'python'
        try:
            t = time.time()
            fg = af.Forge(os.path.join(HERE, 'selftest', 'selftest.forge'))
            ok = [p['name'] for p in fg.packs] == exp['packs']
            n = 0
            for p in fg.packs:
                for f in fg.pack_files(p):
                    ok &= hashlib.sha256(f['data']).hexdigest() == exp['files'][str(f['id'])]
                    n += 1
            name = af.lzo_backend() if backend == 'active' else 'python'
            results.append({'backend': name, 'ok': bool(ok), 'files': n, 'seconds': round(time.time() - t, 3)})
        finally:
            if backend == 'python':
                if old is None:
                    os.environ.pop('ANVIL_LZO', None)
                else:
                    os.environ['ANVIL_LZO'] = old
    log('info' if all(r['ok'] for r in results) else 'ERROR', f'selftest: {results}')
    return {'results': results}


def act_forges(a):
    return {'forges': list_forges(a['game'])}


def act_open(a):
    fg = forge(a['game'], a['forge'])
    pat = a.get('grep') or None
    limit = int(a.get('limit') or 500)
    rx = re.compile(pat, re.I) if pat else None
    packs = [p for p in fg.packs if not rx or rx.search(p['name'])]
    return {'diag': fg.diag, 'total': len(fg.packs), 'matched': len(packs),
            'packs': [{'id': str(p['id']), 'size': p['size'], 'type': f"{p['type']:08X}", 'name': p['name']}
                      for p in packs[:limit]]}


def _pack(fg, pack_id):
    for p in fg.packs:
        if str(p['id']) == str(pack_id):
            return p
    raise ValueError(f'pack {pack_id} not found')


def act_pack(a):
    fg = forge(a['game'], a['forge'])
    p = _pack(fg, a['pack_id'])
    t = time.time()
    raw_head = fg.raw_pack(p)[:64]
    try:
        files = list(fg.pack_files(p))
    except Exception as e:
        log('ERROR', f"pack {p['name']} ({p['id']}): {e}\n{traceback.format_exc()}")
        return {'error': str(e), 'raw_head': raw_head.hex(), 'sections': list(af.LAST_SECTIONS), 'pack': p['name']}
    log('info', f"pack {p['name']}: {len(files)} files, sections {af.LAST_SECTIONS} in {time.time() - t:.2f}s")
    return {'pack': p['name'], 'raw_head': raw_head.hex(), 'sections': list(af.LAST_SECTIONS),
            'seconds': round(time.time() - t, 3),
            'files': [{'id': str(f['id']), 'type': f"{f['type']:08X}", 'type_name': TYPE_NAMES.get(f['type'], ''),
                       'name': f['name'], 'size': len(f['data']), 'head': f['data'][:48].hex()} for f in files]}


def extract_pack(fg, p, dest, file_rx=None, type_filter=None):
    written = []
    d = os.path.join(dest, safe(p['name']))
    for f in fg.pack_files(p):
        if file_rx and not re.search(file_rx, f['name'], re.I):
            continue
        if type_filter and f['type'] not in type_filter:
            continue
        os.makedirs(d, exist_ok=True)
        fn = os.path.join(d, f"{safe(f['name'])}.{f['type']:08X}.{f['id']}.bin")
        with open(fn, 'wb') as o:
            o.write(f['data'])
        written.append({'path': fn, 'size': len(f['data']), 'name': f['name'], 'type': f"{f['type']:08X}"})
    return written


def act_extract(a):
    fg = forge(a['game'], a['forge'])
    p = _pack(fg, a['pack_id'])
    w = extract_pack(fg, p, os.path.join(out_dir(), 'extracted', a['game']), a.get('files') or None)
    log('info', f"extracted {len(w)} files from {p['name']} -> {os.path.join(out_dir(), 'extracted', a['game'])}")
    return {'written': w}


def act_search(a):
    """Pack-name search across every forge of a game (headers only, fast)."""
    rx = re.compile(a['grep'], re.I)
    hits, errors = [], []
    for fi in list_forges(a['game']):
        try:
            fg = forge(a['game'], fi['name'])
        except Exception as e:
            errors.append({'forge': fi['name'], 'error': str(e)})
            log('ERROR', f"open {fi['name']}: {e}")
            continue
        for p in fg.packs:
            if rx.search(p['name']):
                hits.append({'forge': fi['name'], 'id': str(p['id']), 'size': p['size'], 'name': p['name']})
                if len(hits) >= 2000:
                    break
    return {'hits': hits, 'errors': errors}


def act_hex(a):
    path = forge_path(a['game'], a['forge'])
    off, n = int(a.get('offset') or 0), min(int(a.get('length') or 512), 65536)
    with open(path, 'rb') as f:
        f.seek(off)
        b = f.read(n)
    return {'offset': off, 'hex': b.hex()}


def act_bones(a):
    res = anvil_bones.analyze(a['a'], a.get('b') or None, a.get('known') or None)
    res.pop('a_hashes', None)
    log('info', f"bones: {json.dumps({k: v for k, v in res.items() if not isinstance(v, list)})}")
    return res


def act_extracted(_):
    root = os.path.join(out_dir(), 'extracted')
    out = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            out.append(os.path.join(dp, fn))
    return {'files': sorted(out)[:3000]}


def act_log(a):
    since = int(a.get('since') or 0)
    with LOG_LOCK:
        return {'lines': LOG[since:], 'next': len(LOG)}


def forge_index(game, name, progress=True):
    """File-level index of a forge: every pack's files (id, type, name, size). Built once by decompressing every
    pack, then cached in <out>/index/. Packs that fail to decode are listed under 'errors'."""
    path = forge_path(game, name)
    st = os.stat(path)
    # INDEX_VERSION in the name: indexes built by an older reader (e.g. before Syndicate's v2 packs) are ignored
    cache = os.path.join(out_dir(), 'index',
                         f'{game}__{safe(name)}__{st.st_size}_{int(st.st_mtime)}__v{INDEX_VERSION}.json.gz')
    if os.path.isfile(cache):
        with gzip.open(cache, 'rt') as f:
            return json.load(f)
    fg = forge(game, name)
    t = time.time()
    idx = {'forge': name, 'size': st.st_size, 'version': fg.version, 'packs': [], 'errors': []}
    for i, p in enumerate(fg.packs):
        try:
            files = [[str(f['id']), f"{f['type']:08X}", f['name'], len(f['data'])] for f in fg.pack_files(p)]
            idx['packs'].append({'id': str(p['id']), 'name': p['name'], 'sections': list(af.LAST_SECTIONS),
                                 'files': files})
        except Exception as e:
            idx['errors'].append({'pack': p['name'], 'id': str(p['id']), 'error': f'{type(e).__name__}: {e}',
                                  'sections': list(af.LAST_SECTIONS), 'head': fg.raw_pack(p)[:64].hex()})
        if progress and i and i % 200 == 0:
            log('info', f'indexing {name}: {i}/{len(fg.packs)} packs, {time.time() - t:.0f}s')
    idx['seconds'] = round(time.time() - t, 1)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with gzip.open(cache, 'wt') as f:
        json.dump(idx, f)
    log('info' if not idx['errors'] else 'WARN',
        f"indexed {name}: {len(idx['packs'])} packs, {sum(len(p['files']) for p in idx['packs'])} files, "
        f"{len(idx['errors'])} packs failed, {idx['seconds']}s")
    return idx


def act_find_files(a):
    """File-name search inside the packs of one forge (builds the forge's index the first time)."""
    rx = re.compile(a['grep'], re.I)
    idx = forge_index(a['game'], a['forge'])
    hits = []
    for p in idx['packs']:
        for fid, ftype, fname, size in p['files']:
            if rx.search(fname):
                hits.append({'pack': p['name'], 'pack_id': p['id'], 'id': fid, 'type': ftype,
                             'type_name': TYPE_NAMES.get(int(ftype, 16), ''), 'name': fname, 'size': size})
                if len(hits) >= 2000:
                    break
    return {'hits': hits, 'packs': len(idx['packs']), 'errors': idx['errors'][:50], 'seconds': idx.get('seconds')}


def act_extract_file(a):
    fg = forge(a['game'], a['forge'])
    p = _pack(fg, a['pack_id'])
    w = extract_pack(fg, p, os.path.join(out_dir(), 'extracted', a['game']), f"^{re.escape(a['name'])}$")
    log('info', f"extracted {a['name']} from {p['name']}")
    return {'written': w}


# What the cloud session needs: (label, game, forge candidates in order, file-name regex, max files)
BUNDLE_PLAN = [
    ('Unity male skeleton', 'unity', ['DataPC.forge', 'DataPC_10_dlc.forge'], r'^ACU_BaseSkeleton_Male$', 1),
    ('Unity female skeleton', 'unity', ['DataPC_TitleScreenFPP.forge', 'DataPC.forge'], r'^ACU_BaseSkeleton_Female$', 1),
    ('Unity sword attack', 'unity', ['DataPC.forge'], r'^xx_Fight_Sword_Atk_2m_Front_01$', 1),
    ('Unity sword kill (Atk + Dfn)', 'unity', ['DataPC.forge'], r'^xx_Fight_Sword_Kill_Front_01_(Atk|Dfn)$', 2),
    ('Unity sword combo finisher', 'unity', ['DataPC.forge'], r'^xx_Fight_Sword_Combo_Finisher_Right_01$', 1),
    ('Syndicate female skeleton', 'syn', ['DataPC_14_dlc.forge', 'DataPC_ACVI_London.forge'], r'^ACVI_CHR_SHR_Female$', 1),
    ('Syndicate male skeleton', 'syn', ['DataPC_extra.forge', 'DataPC_20_dlc.forge', 'DataPC_14_dlc.forge',
                                        'DataPC_ACVI_London.forge'], r'^ACVI_CHR_SHR_Male$', 1),
    ('Aveline skirt: mesh, cloth, settings, ragdoll', 'syn', ['DataPC_14_dlc.forge'],
     r'^ACVI_CHR_P_EvieFrye_Outfit09_Aveline_Skirt_(LOD0|Cloth|ClothSettings|LiteRagdoll)$', 6),
    ('Aveline leg ball joints', 'syn', ['DataPC_14_dlc.forge'],
     r'^ACVI_CHR_P_EvieFrye_Outfit09_Aveline_(LeftLeg|RightLeg)_BallJointCommonData$', 2),
    ('Aveline outfit skeleton', 'syn', ['DataPC_14_dlc.forge'], r'^ACVI_CHR_P_EvieFrye_Outfit09_Aveline_Body$', 1),
    ('Elise outfit skeleton', 'syn', ['DataPC_14_dlc.forge'], r'^ACVI_CHR_P_EvieFrye_Outfit08_Elise_Body$', 1),
    ('Élise coat cloth settings + colliders (installed)', 'syn', ['DataPC_14_dlc.forge'],
     r'^ACVI_CHR_P_EvieFrye_Outfit08_(Elise_Coat_ClothSettings|Coat_LiteRagdoll)$', 2),
    ('Syndicate cane clip (format comparison)', 'syn', ['DataPC_extra.forge', 'DataPC_14_dlc.forge'],
     r'^ACVI_Fight_xx_Cane', 1),
]


PIPELINE_TEXT = re.compile(r'\.(py|md|txt|json|log|csv)$', re.I)
PIPELINE_MESH = re.compile(r'(k2[3-9]|k3\d).*\.(glb|gltf|log|png|jpg)$', re.I)


def _bundle_pipeline(z, budget):
    """The Mac-side build pipeline, so checks can be written against the real code and meshes:
    acs_kit/ scripts, logs and docs (text, < 512 KB each), and the latest builds' GLB exports and logs."""
    root = CONFIG.get('duleep_dir') or ''
    if not os.path.isdir(root):
        return {'error': f'Duleep_Files not found: {root}'}
    picked, skipped, used = [], [], 0
    cands = []
    for dp, dns, fns in os.walk(root):
        rel = os.path.relpath(dp, root)
        dns[:] = [d for d in dns if d.lower() not in SKIP_DIRS and d not in ('out', 'ishpreet_mod', 'katar', 'Jacob')]
        if rel.count(os.sep) > 3:
            dns[:] = []
        for fn in fns:
            p = os.path.join(dp, fn)
            r = os.path.relpath(p, root)
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            in_kit = r.startswith('acs_kit') or os.sep not in r
            if in_kit and PIPELINE_TEXT.search(fn) and size < 512 * 1024:
                cands.append((0, size, r, p))
            elif PIPELINE_MESH.search(fn) and size < 8 * 1024 * 1024:
                cands.append((1, -os.path.getmtime(p), r, p))  # newest builds first
    for prio, _, r, p in sorted(cands):
        size = os.path.getsize(p)
        if used + size > budget:
            skipped.append(r)
            continue
        z.write(p, 'pipeline/' + r)
        picked.append(r)
        used += size
    return {'files': len(picked), 'bytes': used, 'skipped_for_size': skipped[:200]}


def act_bundle(a):
    """Build claude_bundle_<time>.zip: log, env, diagnostics, forge indexes and the BUNDLE_PLAN files (< 28 MB)."""
    t0 = time.time()
    report = {'env': act_env({}), 'items': [], 'forges': {}}
    zbuf = io.BytesIO()
    z = zipfile.ZipFile(zbuf, 'w', zipfile.ZIP_DEFLATED)
    budget = BUNDLE_LIMIT - 4 * 1024 * 1024  # keep room for log, report and indexes
    used = 0
    indexed = {}
    for game in ('unity', 'syn'):
        try:
            report['forges'][game] = list_forges(game)
        except Exception as e:
            report['forges'][game] = {'error': str(e)}
    for label, game, forges, file_rx, max_files in BUNDLE_PLAN:
        item = {'label': label, 'status': 'not found', 'tried': []}
        report['items'].append(item)
        try:
            names = forge_names(game)
        except Exception as e:
            item.update(status='skipped', error=str(e))
            continue
        for fname in forges:
            if fname.lower() not in names:
                item['tried'].append(f'{fname}: not installed')
                continue
            real = names[fname.lower()]
            try:
                fg = forge(game, real)
                idx = indexed.get((game, real)) or forge_index(game, real)
                indexed[(game, real)] = idx
            except Exception as e:
                item.update(status='forge error', forge=fname, error=str(e))
                log('ERROR', f'bundle: open {fname}: {e}\n{traceback.format_exc()}')
                head_name = f'raw/{safe(fname)}.head4k.bin'
                if head_name not in z.namelist():  # the header bytes are what's needed to fix the parser
                    with open(forge_path(game, real), 'rb') as fh:
                        z.writestr(head_name, fh.read(4096))
                continue
            report['forges'].setdefault('diag', {})[fname] = fg.diag
            wanted = [(p, fl) for p in idx['packs'] for fl in p['files'] if re.search(file_rx, fl[2])][:max_files]
            if not wanted:
                item['tried'].append(f"{fname}: no matching file in {len(idx['packs'])} packs")
                continue
            got = []
            for p_entry, (fid, ftype, nm, size) in wanted:
                if used + size > budget:
                    item.update(status='skipped: over size budget', size=size)
                    break
                p = _pack(fg, p_entry['id'])
                for f in fg.pack_files(p):
                    if str(f['id']) == fid:
                        z.writestr(f"files/{game}/{safe(p['name'])}/{safe(nm)}.{ftype}.{fid}.bin", f['data'])
                        used += size
                        got.append({'name': nm, 'type': ftype, 'id': fid, 'size': size, 'pack': p['name']})
                        break
            if got:
                item.update(status='ok', forge=fname, files=got)
            break
    report['indexes'] = {}
    for (game, real), idx in indexed.items():  # the indexes let the cloud session find anything else later
        blob = gzip.compress(json.dumps(idx).encode(), 9)
        if used + len(blob) < BUNDLE_LIMIT - 1024 * 1024:
            z.writestr(f'index/{game}__{safe(real)}.json.gz', blob, zipfile.ZIP_STORED)
            used += len(blob)
            report['indexes'][real] = f'included ({len(blob) // 1024} KB)'
        else:
            report['indexes'][real] = f'left out: {len(blob) // 1024} KB would pass the size limit'
    known = os.path.join(CONFIG.get('duleep_dir', ''), 'Evie', 'elise_skel_bones.json')
    if os.path.isfile(known):
        z.write(known, 'files/elise_skel_bones.json')
        report['known_bones'] = 'included'
    else:
        report['known_bones'] = f'missing: {known}'
    known = os.path.join(CONFIG.get('duleep_dir', ''), 'Evie', 'elise_skel_bones.json')
    if os.path.isfile(known):
        z.write(known, 'files/elise_skel_bones.json')
        report['known_bones'] = 'included'
    else:
        report['known_bones'] = f'missing: {known}'
    for extra in (('k25', 'k25_report.json'), ('sword', 'sword_plan.json')):
        p = os.path.join(out_dir(), *extra)
        if os.path.isfile(p):
            z.write(p, '/'.join(extra))
    if a.get('pipeline', True):
        report['pipeline'] = _bundle_pipeline(z, BUNDLE_LIMIT - 1024 * 1024 - used)
    report['seconds'] = round(time.time() - t0, 1)
    z.writestr('report.json', json.dumps(report, indent=1, default=str))
    with LOG_LOCK:
        z.writestr('studio_log.txt', '\n'.join(LOG))
    z.close()
    data = zbuf.getvalue()
    path = os.path.join(out_dir(), f"claude_bundle_{time.strftime('%Y%m%d_%H%M%S')}.zip")
    with open(path, 'wb') as f:
        f.write(data)
    log('info', f'bundle written: {path} ({len(data) / 1e6:.1f} MB)')
    return {'path': path, 'size': len(data), 'items': report['items']}


# ----------------------------------------------------------------------------------- k25: Aveline skirt colliders

BONE_NAMES = ['Reference', 'Hips', 'Pelvis', 'Spine', 'Spine1', 'Spine2', 'Spine3', 'Neck', 'Neck1', 'Head'] + [
    s + p for s in ('Left', 'Right') for p in ('UpLeg', 'Leg', 'Foot', 'ToeBase', 'Clavicle', 'Arm', 'ForeArm',
                                               'Hand', 'UpLegRoll', 'LegRoll', 'ArmRoll', 'ForeArmRoll')]


def bone_name(h):
    """Anvil bone IDs are CRC32 of the bone name (confirmed on the user's skeletons)."""
    import zlib
    for n in BONE_NAMES:
        if zlib.crc32(n.encode()) == h:
            return n
    return f'{h:08X}'


def _find_file(fg, pack_name, file_name):
    for i, p in enumerate(fg.packs):
        if p['name'] == pack_name:
            for f in fg.pack_files(p):
                if f['name'] == file_name:
                    return i, p, f
            raise ValueError(f'{file_name} not in pack {pack_name}')
    raise ValueError(f'pack {pack_name} not in {os.path.basename(fg.path)}')


def _id_slots(data, own):
    """Offsets of u64 values that are this file's own ID or its numbered sub-objects (own+1, own+2, ...)."""
    return [(i, struct.unpack_from('<Q', data, i)[0]) for i in range(len(data) - 7)
            if 0 <= struct.unpack_from('<Q', data, i)[0] - own < 64]


def _bones_in(data):
    import zlib
    names = {zlib.crc32(n.encode()): n for n in BONE_NAMES}
    return sorted({names[h] for h in names if struct.pack('<I', h) in data})


def act_build_k25(a):
    """Ishpreet k25: put Aveline's closed-skirt ClothSettings + LiteRagdoll (colliders on both thighs and shins)
    into the installed Élise coat-cloth pack, keeping Élise's file IDs. Writes a .data pack for forge.install."""
    names = forge_names('syn')
    if 'datapc_14_dlc.forge' not in names:
        raise ValueError('DataPC_14_dlc.forge not found in the Syndicate folder')
    fg = forge('syn', names['datapc_14_dlc.forge'])
    target_pack = 'ACVI_CHR_P_EvieFrye_Outfit08_Elise_Coat_Cloth'
    i_t, p_t, set_t = _find_file(fg, target_pack, 'ACVI_CHR_P_EvieFrye_Outfit08_Elise_Coat_ClothSettings')
    _, _, rag_t = _find_file(fg, target_pack, 'ACVI_CHR_P_EvieFrye_Outfit08_Coat_LiteRagdoll')
    donor_pack = 'ACVI_CHR_P_EvieFrye_Outfit09_Aveline_Skirt_Cloth'
    _, _, set_d = _find_file(fg, donor_pack, 'ACVI_CHR_P_EvieFrye_Outfit09_Aveline_Skirt_ClothSettings')
    _, _, rag_d = _find_file(fg, donor_pack, 'ACVI_CHR_P_EvieFrye_Outfit09_Aveline_Skirt_LiteRagdoll')
    for t, d in ((set_t, set_d), (rag_t, rag_d)):
        if t['type'] != d['type'] or len(t['data']) != len(d['data']):
            raise ValueError(f"{d['name']} ({len(d['data'])} B, {d['type']:08X}) does not match "
                             f"{t['name']} ({len(t['data'])} B, {t['type']:08X})")
    # ClothSettings: plain values after the header, so only the own ID changes
    new_set = bytearray(set_d['data'])
    if struct.unpack_from('<Q', new_set, 1)[0] != set_d['id']:
        raise ValueError('ClothSettings header is not (1 byte, own id, type)')
    struct.pack_into('<Q', new_set, 1, set_t['id'])
    # LiteRagdoll: own ID + numbered sub-objects. Map them onto Élise's by position; refuse if layouts differ.
    slots_d = _id_slots(rag_d['data'], rag_d['id'])
    slots_t = _id_slots(rag_t['data'], rag_t['id'])
    if [s[0] for s in slots_d] != [s[0] for s in slots_t]:
        raise ValueError(f'LiteRagdoll layouts differ: Aveline id slots {[s[0] for s in slots_d]}, '
                         f'Élise {[s[0] for s in slots_t]}; not swapping blindly')
    new_rag = bytearray(rag_d['data'])
    for (off, _), (_, val_t) in zip(slots_d, slots_t):
        struct.pack_into('<Q', new_rag, off, val_t)
    raw = fg.raw_pack(p_t)
    out = af.rebuild_pack(raw, {set_t['id']: bytes(new_set), rag_t['id']: bytes(new_rag)})
    d = os.path.join(out_dir(), 'k25')
    os.makedirs(d, exist_ok=True)
    new_path = os.path.join(d, f'dlc14_{i_t}_CoatCloth_k25.data')
    old_path = os.path.join(d, f'dlc14_{i_t}_CoatCloth_installed_before_k25.data')
    with open(new_path, 'wb') as f:
        f.write(out)
    with open(old_path, 'wb') as f:
        f.write(raw)
    k23 = os.path.join(CONFIG.get('duleep_dir', ''), 'Evie', f'dlc14_{i_t}_ChunniCloth_k23.data')
    k23_same = None
    if os.path.isfile(k23):
        k23_same = open(k23, 'rb').read() == raw
    floats = lambda b: [round(x, 4) for x in struct.unpack_from('<%df' % ((len(b) - 13) // 4), b, 13)]
    report = {
        'pack_index': i_t, 'pack': p_t['name'], 'written': new_path, 'size': len(out), 'rollback': old_path,
        'installed_pack_equals_k23_file': k23_same, 'k23_file': k23,
        'colliders_before (Élise coat)': _bones_in(rag_t['data']),
        'colliders_after (Aveline skirt)': _bones_in(rag_d['data']),
        'ragdoll_id_slots': [s[0] for s in slots_t],
        'settings_before': floats(set_t['data']), 'settings_after': floats(set_d['data']),
        'install': f"forge.install({{{i_t}: '{new_path}'}}, forge_path=<dlc_14 forge>)  # via acs_kit, game closed",
        'rollback_install': f"forge.install({{{i_t}: 'Evie/dlc14_{i_t}_ChunniCloth_k23.data'}}, forge_path=<dlc_14 forge>)",
    }
    with open(os.path.join(d, 'k25_report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    log('info', f"k25 built: {new_path} ({len(out)} B); colliders {report['colliders_before (Élise coat)']} -> "
                f"{report['colliders_after (Aveline skirt)']}; installed == k23 file: {k23_same}")
    return report


# ----------------------------------------------------------------------------------- Sword (Unity -> Syndicate)

# most specific first: '_Atk' is also the attacker suffix of kills, so it is checked last
SWORD_FAMILIES = ['Kill', 'PerfectParry', 'Parry', 'Counter', 'Combo', 'StrongAtk', 'Sig', 'Ground', 'Nonlethal',
                  'ShoulderCharge', 'Unsheath', 'Sheath', 'Dodge', 'Idle', 'Strafe', 'Turn', 'Attack', 'Atk']


def _family(name):
    for k in SWORD_FAMILIES:
        if f'_{k}' in name:
            return k
    return 'other'


def _pair_key(name):
    """Attacker/defender clips share a name up to _Atk/_Dfn: they must be ported (and swapped) together."""
    m = re.match(r'(.*)_(Atk|Dfn)(_.*)?$', name)
    return (m.group(1) + (m.group(3) or '')) if m else None


def _skeleton_bones(game, forge_name, file_rx):
    idx = forge_index(game, forge_name)
    fg = forge(game, forge_name)
    for p in idx['packs']:
        for fid, ftype, nm, size in p['files']:
            if ftype == '24AECB7C' and re.search(file_rx, nm):
                for f in fg.pack_files(_pack(fg, p['id'])):
                    if str(f['id']) == fid:
                        b, mk = f['data'], struct.pack('<I', 0x95741049)
                        out, i = set(), b.find(mk)
                        while i != -1:
                            out.add(struct.unpack_from('<I', b, i + 4)[0])
                            i = b.find(mk, i + 4)
                        return out
    raise ValueError(f'skeleton {file_rx} not found in {forge_name}')


def act_sword_catalog(a):
    """Unity sword clips (player/shared xx_) and Syndicate cane/kukri/knuckle clips, with Atk/Dfn pairing."""
    style = a.get('style') or 'Sword'
    u_name = forge_names('unity').get('datapc.forge')
    s_name = forge_names('syn').get('datapc_extra.forge')
    if not u_name or not s_name:
        raise ValueError('needs Unity DataPC.forge and Syndicate DataPC_extra.forge (Setup tab)')
    ui, si = forge_index('unity', u_name), forge_index('syn', s_name)

    def clips(idx, rx):
        out = []
        for p in idx['packs']:
            for fid, ftype, nm, size in p['files']:
                if ftype == '0FA3067F' and re.search(rx, nm):
                    out.append({'name': nm, 'id': fid, 'size': size, 'pack': p['name'], 'pack_id': p['id'],
                                'family': _family(nm), 'pair': _pair_key(nm)})
        return out
    unity = clips(ui, rf'^xx_Fight_{style}_')
    target = a.get('target') or 'Cane'
    syn = clips(si, rf'^ACVI_Fight_xx_{target}')
    for lst in (unity, syn):
        pairs = {}
        for c in lst:
            if c['pair']:
                pairs.setdefault(c['pair'], []).append(c['name'])
        for c in lst:
            c['paired_with'] = [n for n in pairs.get(c['pair'], []) if n != c['name']] if c['pair'] else []
    return {'unity': unity, 'syn': syn, 'unity_forge': u_name, 'syn_forge': s_name}


def act_sword_check(a):
    """Bone coverage of one Unity clip against Syndicate's male and female base skeletons."""
    u_name, s_name = forge_names('unity')['datapc.forge'], forge_names('syn')['datapc_extra.forge']
    ubones = _skeleton_bones('unity', u_name, r'^ACU_BaseSkeleton_Male$')
    smale = _skeleton_bones('syn', s_name, r'^ACVI_CHR_SHR_Male$')
    f14 = forge_names('syn').get('datapc_14_dlc.forge')
    sfem = _skeleton_bones('syn', f14, r'^ACVI_CHR_SHR_Female$') if f14 else set()
    fg = forge('unity', u_name)
    data = None
    for f in fg.pack_files(_pack(fg, a['pack_id'])):
        if str(f['id']) == a['id']:
            data = f['data']
    if data is None:
        raise ValueError('clip not found')
    used = {h for h in ubones if struct.pack('<I', h) in data}
    res = {'clip': a['name'], 'bones_animated': len(used), 'in_syndicate_male': len(used & smale),
           'in_syndicate_female': len(used & sfem) if sfem else None,
           'missing_male': [bone_name(h) for h in sorted(used - smale)],
           'missing_female': [bone_name(h) for h in sorted(used - sfem)] if sfem else None}
    res['direct_port'] = not res['missing_male'] and (not sfem or not res['missing_female'])
    log('info', f"sword check {a['name']}: {len(used)} bones, male ok {len(used & smale)}, "
                f"direct port: {res['direct_port']}")
    return res


def act_sword_plan(a):
    """Save the Unity -> Syndicate slot mapping (pairs expanded) and extract the chosen Unity clips for the
    AnvilToolkit XML step. Returns the plan."""
    rows = a.get('rows') or []
    if not rows:
        raise ValueError('no rows: pick at least one Unity clip and a Syndicate slot')
    cat = act_sword_catalog({'style': a.get('style'), 'target': a.get('target')})
    u = {c['name']: c for c in cat['unity']}
    s = {c['name']: c for c in cat['syn']}
    plan, problems = [], []
    for r in rows:
        uc, sc = u.get(r['unity']), s.get(r['syn'])
        if not uc or not sc:
            problems.append(f"unknown clip in row {r}")
            continue
        plan.append({'unity': uc, 'syn': sc})
        # a pair on one side needs its partner mapped too, or kills desync (katar m1 lesson)
        if uc['paired_with'] and not sc['paired_with']:
            problems.append(f"{uc['name']} has partner {uc['paired_with']} but slot {sc['name']} has none")
        for partner in uc['paired_with']:
            if partner not in [x['unity'] for x in rows]:
                problems.append(f"{uc['name']}: its partner {partner} is not mapped")
    d = os.path.join(out_dir(), 'sword')
    os.makedirs(d, exist_ok=True)
    fg = forge('unity', cat['unity_forge'])
    written = []
    for row in plan:
        c = row['unity']
        for f in fg.pack_files(_pack(fg, c['pack_id'])):
            if str(f['id']) == c['id']:
                fn = os.path.join(d, f"{safe(c['name'])}.0FA3067F.{c['id']}.bin")
                with open(fn, 'wb') as o:
                    o.write(f['data'])
                written.append(fn)
                break
    out = {'plan': [{'unity': r['unity']['name'], 'unity_id': r['unity']['id'], 'syn_slot': r['syn']['name'],
                     'syn_slot_id': r['syn']['id'], 'syn_pack': r['syn']['pack']} for r in plan],
           'problems': problems, 'extracted': written}
    with open(os.path.join(d, 'sword_plan.json'), 'w') as f:
        json.dump(out, f, indent=1)
    log('info' if not problems else 'WARN', f'sword plan: {len(plan)} rows, {len(problems)} problems')
    return out


# ----------------------------------------------------------------------------------- fight data export (multi-part)

FIGHT_TYPES = {'C0C861CD': 'AtomGraph', '2E772CD8': 'UIEnumBinding', 'C69075AB': 'InventoryItemSettings',
               '0F76DBDC': 'AvatarCustomizationManager'}
FIGHT_NAME_RX = re.compile(r'Weapon|Fight|Sword|Cane|Kukri|Knife|Knuckle|Heavy|Long|Dagger|Gear|Inventory|Avatar',
                           re.I)


def _collect(game, forge_basename, want):
    """want(pack_name, file_type, file_name, size) -> bool. Yields (path_in_zip, bytes)."""
    real = forge_names(game).get(forge_basename.lower())
    if not real:
        log('WARN', f'fight export: {forge_basename} not found for {game}')
        return
    idx = forge_index(game, real)
    fg = forge(game, real)
    for p in idx['packs']:
        hits = {fid for fid, ft, nm, sz in p['files'] if want(p['name'], ft, nm, sz)}
        if not hits:
            continue
        for f in fg.pack_files(_pack(fg, p['id'])):
            if str(f['id']) in hits:
                yield (f"{game}/{safe(p['name'])}/{safe(f['name'])}.{f['type']:08X}.{f['id']}.bin", f['data'])


def act_fight_export(a):
    """Everything needed to work out how a fighting style is selected: both fight graphs, the weapon / inventory /
    UI-binding / gear-tab records of both games, and Syndicate's leftover Sword/Long/Heavy clips. Written as
    claude_fight_partN.zip files under 28 MB each (gzip inside; big files split across parts, sha256 in manifest)."""
    t0 = time.time()
    blobs = []
    graph = lambda pn, ft, nm, sz: ft == 'C0C861CD' and nm.startswith('NewDemo')
    settings = lambda pn, ft, nm, sz: pn == 'Game Bootstrap Settings' and (
        ft in FIGHT_TYPES or (FIGHT_NAME_RX.search(nm) and sz < 2 * 1024 * 1024))
    leftovers = lambda pn, ft, nm, sz: ft == '0FA3067F' and re.search(r'_Fight_(Sword|Long|Heavy)_|_xx_Heavy', nm)
    for game, fb, want in (('syn', 'DataPC_extra.forge', graph), ('unity', 'DataPC.forge', graph),
                           ('syn', 'DataPC.forge', settings), ('unity', 'DataPC.forge', settings),
                           ('syn', 'DataPC_extra.forge', leftovers)):
        try:
            for path, data in _collect(game, fb, want):
                blobs.append((path, data))
        except Exception as e:
            log('ERROR', f'fight export {game}/{fb}: {e}\n{traceback.format_exc()}')
    written = _write_parts(blobs, 'claude_fight')
    log('info', f'fight export: {len(blobs)} files in {len(written)} parts, {time.time() - t0:.0f}s')
    return {'parts': written, 'files': len(blobs), 'seconds': round(time.time() - t0, 1),
            'summary': [{'path': p, 'size': len(d)} for p, d in blobs if len(d) > 1e6]}


def _original_pack(game, forge_basename, index):
    """A pack as it was before acs_kit relocated it: the relocation log in Duleep_Files keeps the original
    20-byte index entry (offset, id, size), and relocation never overwrites the original bytes."""
    path = os.path.join(CONFIG.get('duleep_dir') or '', f'{forge_basename}.reloc.json')
    try:
        entries = json.load(open(path))['entries']
    except (OSError, ValueError, KeyError):
        return None
    for e in entries:
        if e.get('index') == index:
            off, fid, size = struct.unpack('<QQI', bytes.fromhex(e['oe']))
            return {'id': fid, 'offset': off, 'size': size, 'type': 0, 'name': f'original_{index}'}
    return None


def act_original_graph_export(a):
    """Syndicate's unmodded fight graph (before the katar edits), read from its pre-relocation location."""
    real = forge_names('syn').get('datapc_extra.forge')
    if not real:
        raise ValueError('DataPC_extra.forge not found')
    fg = forge('syn', real)
    p = _original_pack('syn', 'DataPC_extra.forge', int(a.get('index', 6969)))
    if p is None:
        raise ValueError('no relocation entry for pack 6969 in Duleep_Files/DataPC_extra.forge.reloc.json: '
                         'the installed graph is the original one, use Export fight data instead')
    if p['offset'] + p['size'] > fg.file_size:
        raise ValueError('the original bytes are past the end of the forge (it was truncated?)')
    blobs = [(f"syn_original/{safe(f['name'])}.{f['type']:08X}.{f['id']}.bin", f['data'])
             for f in fg.pack_files(p) if f['type'] == 0xC0C861CD]
    if not blobs:
        raise ValueError('no AtomGraph in the original pack')
    written = _write_parts(blobs, 'claude_graph_original')
    log('info', f'original graph export: {[len(d) for _, d in blobs]} bytes -> {len(written)} parts')
    return {'parts': written, 'files': len(blobs)}


def _write_parts(blobs, prefix):
    """gzip each blob, split into <= 20 MB pieces, pack into zips under BUNDLE_LIMIT (manifest with sha256)."""
    manifest = {'files': [], 'created': time.strftime('%Y-%m-%d %H:%M:%S')}
    chunks = []  # (zip path, bytes) after gzip, split into <= 20 MB pieces
    for path, data in blobs:
        gz = gzip.compress(data, 9)
        n = (len(gz) + 20 * 1024 * 1024 - 1) // (20 * 1024 * 1024)
        manifest['files'].append({'path': path, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                  'gz_parts': n})
        for k in range(n):
            chunks.append((f'{path}.gz.{k:02d}', gz[k * 20 * 1024 * 1024:(k + 1) * 20 * 1024 * 1024]))
    parts, cur, cur_size = [], [], 0
    for c in chunks:  # 25 MB per part: the user's 2026-10-10 part 1 came out at 30.7 MB with the old 28 MB target
        if cur and cur_size + len(c[1]) > 25 * 1000 * 1000:
            parts.append(cur)
            cur, cur_size = [], 0
        cur.append(c)
        cur_size += len(c[1])
    if cur:
        parts.append(cur)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    written = []
    for i, part in enumerate(parts, 1):
        path = os.path.join(out_dir(), f'{prefix}_{stamp}_part{i}of{len(parts)}.zip')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as z:
            for name, data in part:
                z.writestr(name, data)
            if i == 1:
                z.writestr('manifest.json', json.dumps(manifest, indent=1))
                with LOG_LOCK:
                    z.writestr('studio_log.txt', '\n'.join(LOG))
        written.append({'path': path, 'size': os.path.getsize(path)})
    return written


# ----------------------------------------------------------------------------------- performance (AC.ini, bottle)

def _bottle_root():
    d = CONFIG.get('syn_dir') or ''
    while d and d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, 'drive_c')):
            return d
        d = os.path.dirname(d)
    return None


def _ac_ini():
    """AC.ini of Syndicate inside the bottle (Documents/Assassin's Creed Syndicate/AC.ini), any user name."""
    root = _bottle_root()
    if not root:
        return None
    users = os.path.join(root, 'drive_c', 'users')
    for u in sorted(os.listdir(users)) if os.path.isdir(users) else []:
        for docs in ('Documents', 'My Documents'):
            base = os.path.join(users, u, docs)
            if not os.path.isdir(base):
                continue
            for n in sorted(os.listdir(base)):
                if 'syndicate' in n.lower():
                    p = os.path.join(base, n, 'AC.ini')
                    if os.path.isfile(p):
                        return p
    return None


def _parse_ini(text):
    sections, cur = {}, None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            cur = s[1:-1]
            sections.setdefault(cur, {})
        elif '=' in s and cur is not None and not s.startswith(';'):
            k, v = s.split('=', 1)
            sections[cur][k.strip()] = v.strip()
    return sections


def act_perf_read(a):
    root = _bottle_root()
    out = {'bottle': root, 'ac_ini': _ac_ini(), 'ini': None, 'bottle_conf': [], 'reshade': {}}
    if out['ac_ini']:
        out['ini'] = _parse_ini(open(out['ac_ini'], encoding='utf-8', errors='replace').read())
    if root and os.path.isfile(os.path.join(root, 'cxbottle.conf')):
        for line in open(os.path.join(root, 'cxbottle.conf'), encoding='utf-8', errors='replace'):
            if re.search(r'^\s*\[|DXVK|D3DM|DXMT|METAL|MSYNC|ESYNC|SYNC|GRAPHICS|BACKEND|HUD|WINE', line, re.I):
                out['bottle_conf'].append(line.rstrip())
    sd = CONFIG.get('syn_dir') or ''
    for n in ('dxgi.dll', 'd3d11.dll', 'ReShade.ini', 'ReShade.log', 'reshade-shaders', 'dxvk.conf'):
        p = os.path.join(sd, n)
        if os.path.exists(p):
            out['reshade'][n] = os.path.getsize(p) if os.path.isfile(p) else 'folder'
    log_p = os.path.join(sd, 'ReShade.log')
    if os.path.isfile(log_p):
        out['reshade_log_tail'] = open(log_p, encoding='utf-8', errors='replace').read()[-3000:]
    out['reshade_verdict'] = ('ReShade.log present: ReShade loaded at least once (see the tail)' if 'ReShade.log' in
                              out['reshade'] else ('ReShade files present but no ReShade.log: it is NOT loading'
                                                   if out['reshade'] else 'ReShade not installed in the game folder'))
    log('info', f"perf read: AC.ini {out['ac_ini']}, bottle {root}, reshade {out['reshade']}")
    return out


def act_perf_write(a):
    """Set AC.ini keys ({section: {key: value}}), keeping every other line as it is. Backs the file up first."""
    p = _ac_ini()
    if not p:
        raise ValueError('AC.ini not found in the bottle (start the game once so it creates it)')
    raw = open(p, 'rb').read()
    crlf = b'\r\n' in raw  # keep the game's own line endings
    text = raw.decode('utf-8', errors='replace').replace('\r\n', '\n')
    bdir = os.path.join(out_dir(), 'acini_backups')
    os.makedirs(bdir, exist_ok=True)
    backup = os.path.join(bdir, f"AC_{time.strftime('%Y%m%d_%H%M%S')}.ini")
    with open(backup, 'wb') as f:
        f.write(raw)
    want = {s: dict(kv) for s, kv in (a.get('set') or {}).items()}
    lines, cur, done = text.splitlines(), None, set()
    out = []
    for line in lines:
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            if cur in want:  # append keys this section didn't have yet
                out += [f'{k}={v}' for k, v in want[cur].items() if (cur, k) not in done]
                done |= {(cur, k) for k in want[cur]}
            cur = s[1:-1]
        elif '=' in s and cur in want:
            k = s.split('=', 1)[0].strip()
            if k in want[cur]:
                line = f'{k}={want[cur][k]}'
                done.add((cur, k))
        out.append(line)
    if cur in want:
        out += [f'{k}={v}' for k, v in want[cur].items() if (cur, k) not in done]
        done |= {(cur, k) for k in want[cur]}
    for sec, kv in want.items():  # sections that did not exist
        missing = [(k, v) for k, v in kv.items() if (sec, k) not in done]
        if missing:
            out += ['', f'[{sec}]'] + [f'{k}={v}' for k, v in missing]
    with open(p, 'wb') as f:
        f.write(('\r\n' if crlf else '\n').join(out).encode('utf-8') + (b'\r\n' if crlf else b'\n'))
    log('info', f'AC.ini updated: {json.dumps(want)}; backup {backup}')
    return {'ac_ini': p, 'backup': backup, 'ini': _parse_ini(open(p, encoding='utf-8').read())}


def act_reveal(a):
    p = a.get('path') or out_dir()
    if sys.platform == 'darwin':
        subprocess.run(['open', '-R', p] if os.path.isfile(p) else ['open', p], check=False)
    return {'ok': True}


ACTIONS = {name[4:]: fn for name, fn in globals().items() if name.startswith('act_')}

# --------------------------------------------------------------------------------------------- HTTP


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype='application/json'):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/' and parse_qs(u.query).get('t', [''])[0] == TOKEN:
            html = open(os.path.join(HERE, 'studio_ui.html'), encoding='utf-8').read()
            return self._send(200, html.replace('__TOKEN__', TOKEN), 'text/html; charset=utf-8')
        if u.path == '/favicon.ico':
            return self._send(204, b'', 'image/x-icon')
        self._send(403, 'Open the link printed by Ishpreet Studio.', 'text/plain')

    def do_POST(self):
        u = urlparse(self.path)
        if self.headers.get('X-Token') != TOKEN or not u.path.startswith('/api/'):
            return self._send(403, json.dumps({'error': 'bad token'}))
        name = u.path[5:]
        n = int(self.headers.get('Content-Length') or 0)
        try:
            args = json.loads(self.rfile.read(n) or b'{}')
        except ValueError:
            args = {}
        fn = ACTIONS.get(name)
        if not fn:
            return self._send(404, json.dumps({'error': f'unknown action {name}'}))
        t = time.time()
        try:
            res = fn(args)
            if name not in ('log',):
                log('debug', f'{name} {json.dumps(args)[:300]} ok in {time.time() - t:.2f}s')
            self._send(200, json.dumps(res, default=str))
        except Exception as e:
            tb = traceback.format_exc()
            log('ERROR', f'{name} {json.dumps(args)[:300]}: {e}\n{tb}')
            self._send(200, json.dumps({'error': f'{type(e).__name__}: {e}', 'traceback': tb}))


def main():
    load_config()
    log('info', f'Ishpreet Studio {VERSION}, python {sys.version.split()[0]}, {platform.platform()}, '
                f'LZO backend: {af.lzo_backend()}')
    bad = [k for k in ('unity_dir', 'syn_dir') if not _is_game_dir(k[:-4], CONFIG.get(k) or '')]
    if bad:  # empty, or saved earlier but not actually that game's folder
        found = detect()
        for k in bad:
            if found[k]:
                log('info', f'{k}: {CONFIG.get(k)!r} -> {found[k][0]!r}')
                CONFIG[k] = found[k][0]
        save_config()
    srv = None
    for port in range(8765, 8800):
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            continue
    if srv is None:
        sys.exit('no free port between 8765 and 8799')
    url = f'http://127.0.0.1:{srv.server_address[1]}/?t={TOKEN}'
    log('info', f'open {url}  (close this window or press Ctrl+C to quit)')
    if '--no-browser' not in sys.argv:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
