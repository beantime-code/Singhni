"""Ishpreet Studio: a local, browser-based front end for the forge tools. No VM, no Terminal, no installs.

Start it by double-clicking "Ishpreet Studio.command" (next to this folder), or: python3 ishpreet_studio.py
It serves http://127.0.0.1:<port>/?t=<token> to this Mac only, and opens your browser.

Everything it does is logged (with full tracebacks) to <output folder>/studio_log.txt and shown in the Debug
tab. "Bundle for Claude" packs the log, the forge header diagnostics and the small game files the cloud
session needs (skeletons, a few sword clips, the Aveline skirt pack) into one zip under 28 MB.
"""
import hashlib
import io
import json
import os
import platform
import re
import secrets
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

VERSION = '1.0'
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


def detect():
    """Look for the game folders inside CrossOver bottles, plus Duleep_Files."""
    found = {'unity_dir': [], 'syn_dir': []}
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
                    if os.path.isdir(p):
                        found[f'{key}_dir'].append(p)
    log('info', f'detect: {json.dumps(found)}')
    return found


def game_dir(game):
    d = CONFIG.get(f'{game}_dir', '')
    if not d or not os.path.isdir(d):
        raise ValueError(f'{"Unity" if game == "unity" else "Syndicate"} folder not set or missing: {d!r} (Setup tab)')
    return d


def list_forges(game):
    d = game_dir(game)
    out = []
    for n in sorted(os.listdir(d)):
        if n.lower().endswith('.forge'):
            out.append({'name': n, 'size': os.path.getsize(os.path.join(d, n))})
    return out


_FORGES = {}


def forge(game, name):
    path = os.path.join(game_dir(game), os.path.basename(name))
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
    return CONFIG


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
    path = os.path.join(game_dir(a['game']), os.path.basename(a['forge']))
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


# Files the cloud session needs, in priority order: (label, game, forge candidates, pack regex, file regex)
BUNDLE_PLAN = [
    ('Unity male skeleton', 'unity', ['DataPC_10_dlc.forge', 'DataPC.forge'], r'^ACU_BaseSkeleton_Male$', None),
    ('Unity female skeleton', 'unity', ['DataPC_ACU_Paris.forge', 'DataPC.forge'], r'^ACU_BaseSkeleton_Female$', None),
    ('Syndicate male skeleton', 'syn', ['DataPC_extra.forge', 'DataPC_20_dlc.forge'], r'^ACVI_CHR_SHR_Male$', None),
    ('Syndicate female skeleton', 'syn', ['DataPC_14_dlc.forge', 'DataPC_ACVI_London.forge'], r'^ACVI_CHR_SHR_Female$', None),
    ('Aveline skirt pack', 'syn', ['DataPC_14_dlc.forge'], r'^ACVI_CHR_P_EvieFrye_Outfit09_Aveline_Skirt_LOD0$', None),
    ('Aveline outfit skeleton', 'syn', ['DataPC_14_dlc.forge'], r'^ACVI_CHR_P_EvieFrye_Outfit09_Aveline_Body$', None),
    ('Elise outfit skeleton', 'syn', ['DataPC_14_dlc.forge'], r'^ACVI_CHR_P_EvieFrye_Outfit08_Elise_Body$', None),
    ('Unity sword attack', 'unity', ['DataPC.forge'], r'^xx_Fight_Sword_Atk_1m_Front_01$', None),
    ('Unity sword kill (Atk)', 'unity', ['DataPC.forge'], r'^xx_Fight_Sword_Kill_Front_01_Atk$', None),
    ('Unity sword kill (Dfn)', 'unity', ['DataPC.forge'], r'^xx_Fight_Sword_Kill_Front_01_Dfn$', None),
]


def act_bundle(a):
    """Build claude_bundle_<time>.zip: log, env, diagnostics and the BUNDLE_PLAN files, capped at 28 MB."""
    t0 = time.time()
    report = {'env': act_env({}), 'items': [], 'forges': {}}
    zbuf = io.BytesIO()
    z = zipfile.ZipFile(zbuf, 'w', zipfile.ZIP_DEFLATED)
    budget = BUNDLE_LIMIT - 2 * 1024 * 1024  # keep room for log + report
    used = 0
    for game in ('unity', 'syn'):
        try:
            report['forges'][game] = list_forges(game)
        except Exception as e:
            report['forges'][game] = {'error': str(e)}
    for label, game, forges, pack_rx, file_rx in BUNDLE_PLAN:
        item = {'label': label, 'status': 'not found'}
        report['items'].append(item)
        try:
            names = {f['name'].lower(): f['name'] for f in list_forges(game)}
        except Exception as e:
            item.update(status='skipped', error=str(e))
            continue
        for fname in forges:
            if fname.lower() not in names:
                continue
            try:
                fg = forge(game, names[fname.lower()])
            except Exception as e:
                item.update(status='forge error', forge=fname, error=str(e))
                log('ERROR', f'bundle: open {fname}: {e}\n{traceback.format_exc()}')
                head_name = f'raw/{safe(fname)}.head4k.bin'
                if head_name not in z.namelist():  # the header bytes are what's needed to fix the parser
                    with open(os.path.join(game_dir(game), names[fname.lower()]), 'rb') as fh:
                        z.writestr(head_name, fh.read(4096))
                continue
            report['forges'].setdefault('diag', {})[fname] = fg.diag
            packs = [p for p in fg.packs if re.search(pack_rx, p['name'])]
            if not packs:
                item.update(status='pack not in forge', forge=fname)
                continue
            p = packs[0]
            try:
                files = [f for f in fg.pack_files(p) if not file_rx or re.search(file_rx, f['name'])]
            except Exception as e:
                raw = fg.raw_pack(p)
                z.writestr(f"raw/{safe(fname)}/{safe(p['name'])}.pack_head.bin", raw[:4096])
                item.update(status='decode error', forge=fname, pack=p['name'], error=str(e),
                            sections=list(af.LAST_SECTIONS), traceback=traceback.format_exc())
                log('ERROR', f"bundle: {label}: {e}\n{traceback.format_exc()}")
                break
            size = sum(len(f['data']) for f in files)
            if used + size > budget:
                item.update(status='skipped: over size budget', forge=fname, pack=p['name'], size=size)
                break
            for f in files:
                z.writestr(f"files/{game}/{safe(p['name'])}/{safe(f['name'])}.{f['type']:08X}.{f['id']}.bin",
                           f['data'])
            used += size
            item.update(status='ok', forge=fname, pack=p['name'], pack_id=str(p['id']), files=len(files),
                        size=size, sections=list(af.LAST_SECTIONS))
            break
    known = os.path.join(CONFIG.get('duleep_dir', ''), 'Evie', 'elise_skel_bones.json')
    if os.path.isfile(known):
        z.write(known, 'files/elise_skel_bones.json')
        report['known_bones'] = 'included'
    else:
        report['known_bones'] = f'missing: {known}'
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
    if not CONFIG.get('unity_dir') or not CONFIG.get('syn_dir'):
        found = detect()
        for k in ('unity_dir', 'syn_dir'):
            if not CONFIG.get(k) and found[k]:
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
