"""Runs acu_freecam.lua (the Cheat Engine script) against an emulated process: the Lua runs in lupa with Cheat
Engine's memory functions backed by a unicorn x86-64 address space, and the hook bytes it writes are EXECUTED by
unicorn through the swapped vtable, the way the game calls them.

    pip install lupa unicorn ; python3 test_freecam.py

Fake game: CameraManager singleton at 0x14521AAD0 -> camera object (vtable of 128 functions, slot 0x288 = a stand-in
ApplyCameraFX that writes pos (1,2,3), a 90-degree yaw quaternion and fov 0.8) + the selector/curve-point chain.
"""
import os
import struct

from lupa import lua54
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9, \
    UC_X86_REG_RSP

HERE = os.path.dirname(os.path.abspath(__file__))
HEAP, RDATA, TEXT, ALLOC, STACK, DRIVER = 0x10000000, 0x150000000, 0x160000000, 0x170000000, 0x180000000, 0x190000000
CAM = HEAP + 0x1000
f32 = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]  # noqa: E731


class Proc:
    def __init__(self):
        u = self.u = Uc(UC_ARCH_X86, UC_MODE_64)
        for base, size in ((0x14521A000, 0x1000), (0x142E68000, 0x1000), (HEAP, 0x100000), (RDATA, 0x2000),
                           (TEXT, 0x10000), (ALLOC, 0x100000), (STACK, 0x10000), (DRIVER, 0x1000)):
            u.mem_map(base, size)
        self.next_alloc = ALLOC
        # 128 virtual functions: slot i returns i in eax; slot 0x288/8 is the stand-in ApplyCameraFX
        fx = b''.join([b'\xc7\x02' + struct.pack('<I', f32(1.0)), b'\xc7\x42\x04' + struct.pack('<I', f32(2.0)),
                       b'\xc7\x42\x08' + struct.pack('<I', f32(3.0)), b'\xc7\x42\x0c' + struct.pack('<I', f32(1.0)),
                       b'\x41\xc7\x00' + struct.pack('<I', 0), b'\x41\xc7\x40\x04' + struct.pack('<I', 0),
                       b'\x41\xc7\x40\x08' + struct.pack('<I', f32(0.70710677)),
                       b'\x41\xc7\x40\x0c' + struct.pack('<I', f32(0.70710677)),
                       b'\x41\xc7\x01' + struct.pack('<I', f32(0.8)), b'\xc3'])
        for i in range(128):
            code = fx if i == 0x288 // 8 else b'\xb8' + struct.pack('<I', i) + b'\xc3'
            u.mem_write(TEXT + 0x80 * i, code)
            u.mem_write(RDATA + 8 + 8 * i, struct.pack('<Q', TEXT + 0x80 * i))
        u.mem_write(RDATA, struct.pack('<Q', 0xDEADBEEF))                 # RTTI locator slot
        mgr = HEAP
        u.mem_write(0x14521AAD0, struct.pack('<Q', mgr))
        u.mem_write(mgr + 0x40, struct.pack('<QHH', HEAP + 0x800, 1, 1))
        u.mem_write(HEAP + 0x800, struct.pack('<Q', CAM))
        u.mem_write(CAM, struct.pack('<Q', RDATA + 8))
        u.mem_write(CAM + 0xA90, struct.pack('<4f', 1.0, 3.0, 3.0, 1.0))  # look-at: from (1,2,3) towards +y
        sb, node, cd, hp, varr = HEAP + 0x3000, HEAP + 0x3100, HEAP + 0x3200, HEAP + 0x3800, HEAP + 0x3900
        u.mem_write(CAM + 0x9B8, struct.pack('<Q', sb))
        u.mem_write(sb, struct.pack('<QiI', node, 1, 0x80000001))
        u.mem_write(node + 0x20, struct.pack('<Q', cd))
        u.mem_write(cd + 0x2F0, struct.pack('<QHH', HEAP + 0x3700, 1, 1))
        u.mem_write(HEAP + 0x3700, struct.pack('<Q', hp))
        u.mem_write(hp + 0x08, struct.pack('<QHH', varr, 2, 2))
        self.vps = [HEAP + 0x4000, HEAP + 0x4100]
        for k, vp in enumerate(self.vps):
            u.mem_write(varr + 8 * k, struct.pack('<Q', vp))
            u.mem_write(vp + 0x60, struct.pack('<f', 3.0 + k))           # distance
            u.mem_write(vp + 0x6C, struct.pack('<f', 0.75))              # fov
        self.keys = set()

    def call_slot(self, slot):
        """what the game does: mov rax,[rcx]; call [rax+slot*8]; with pos/quat/fov buffers in rdx/r8/r9"""
        u = self.u
        drv = b'\x48\x8b\x01' + b'\xff\x90' + struct.pack('<I', slot * 8) + b'\xf4'
        u.mem_write(DRIVER, drv)
        buf = HEAP + 0x6000
        u.mem_write(buf, b'\0' * 0x40)
        for r, v in ((UC_X86_REG_RCX, CAM), (UC_X86_REG_RDX, buf), (UC_X86_REG_R8, buf + 0x10),
                     (UC_X86_REG_R9, buf + 0x20), (UC_X86_REG_RSP, STACK + 0x8000), (UC_X86_REG_RAX, 0)):
            u.reg_write(r, v)
        u.emu_start(DRIVER, DRIVER + len(drv) - 1)
        b = bytes(u.mem_read(buf, 0x24))
        return (u.reg_read(UC_X86_REG_RAX) & 0xffffffff, struct.unpack('<4f', b[:16]),
                struct.unpack('<4f', b[16:32]), struct.unpack('<f', b[32:36])[0])

    def lua(self):
        L = lua54.LuaRuntime()
        u = self.u
        g = L.globals()
        rd = lambda a, n: bytes(u.mem_read(a, n))  # noqa: E731
        g.readQword = lambda a: struct.unpack('<Q', rd(a, 8))[0]
        g.writeQword = lambda a, v: u.mem_write(a, struct.pack('<Q', v & (2 ** 64 - 1)))
        g.readFloat = lambda a: struct.unpack('<f', rd(a, 4))[0]
        g.writeFloat = lambda a, v: u.mem_write(a, struct.pack('<f', v))
        g.readInteger = lambda a: struct.unpack('<I', rd(a, 4))[0]
        g.writeInteger = lambda a, v: u.mem_write(a, struct.pack('<I', v))
        g.readSmallInteger = lambda a: struct.unpack('<H', rd(a, 2))[0]
        g.readBytes = lambda a, n, t=True: L.table(*rd(a, n))
        g.writeBytes = lambda a, t: u.mem_write(a, bytes(int(t[i]) for i in range(1, len(t) + 1)))
        g.floatToByteTable = lambda v: L.table(*struct.pack('<f', v))

        def alloc(n):
            a = self.next_alloc
            self.next_alloc += (n + 0xfff) & ~0xfff
            return a
        g.allocateMemory = alloc
        self.messages = []
        g.showMessage = lambda m: self.messages.append(m)
        g.print = lambda *a: self.messages.append(' '.join(map(str, a)))
        self.on_sleep = None
        g.sleep = lambda ms: self.on_sleep and self.on_sleep(ms)
        g.isKeyPressed = lambda k: k in self.keys
        self.tick = [0]
        g.getTickCount = lambda: self.tick[0]
        g.createTimer = lambda *a: L.table()
        g.registerSymbol = lambda *a: None
        F = L.execute(open(os.path.join(HERE, 'acu_freecam.lua')).read())
        return L, F


def test_hook_passthrough_override_probe_curves():
    p = Proc()
    L, F = p.lua()
    # before: plain game
    assert p.call_slot(0x288 // 8)[1][:3] == (1.0, 2.0, 3.0)
    assert F.install()
    vt = p.u.mem_read(CAM, 8)
    assert struct.unpack('<Q', vt)[0] != RDATA + 8
    # every other virtual still reaches the game's function, through a counter stub
    for s in (0, 5, 80, 82, 127):
        assert p.call_slot(s)[0] == s
    # the camera hook passes the game's values through while free camera is off, and records them
    r, pos, quat, fov = p.call_slot(0x288 // 8)
    assert pos[:3] == (1.0, 2.0, 3.0) and abs(fov - 0.8) < 1e-6 and F.calls() == 1
    # probe: per-slot rates while the game keeps calling
    p.on_sleep = lambda ms: [p.call_slot(0x288 // 8) for _ in range(120)] + [p.call_slot(7) for _ in range(60)]
    out = F.probe(2)
    txt = '\n'.join(p.messages)
    assert 'slot 0x038: 30/s' in txt and 'ApplyCameraFX (hook): 60/s' in txt, txt
    # free camera: starts exactly at the game's camera, then the keys move it
    assert F.free_on()
    r, pos, quat, fov = p.call_slot(0x288 // 8)
    assert pos[:3] == (1.0, 2.0, 3.0) and abs(fov - 0.8) < 1e-6
    fl = [F.fwd_local[i] for i in (1, 2, 3)]
    # game quat = 90 deg about z; look-at is +y from the camera, so local forward must be +x (rotated onto +y)
    assert fl == [1, 0, 0], fl
    p.keys = {ord('I')}
    p.tick[0] += 100
    F.tick()
    r, pos, quat, fov = p.call_slot(0x288 // 8)
    assert abs(pos[0] - 1.0) < 1e-4 and abs(pos[1] - 2.3) < 1e-4 and abs(pos[2] - 3.0) < 1e-4, pos  # 3 m/s * 0.1 s on +y
    p.keys = {0x25}                                    # Left arrow: yaw
    p.tick[0] += 100
    F.tick()
    q2 = p.call_slot(0x288 // 8)[2]
    assert abs(sum(x * x for x in q2) - 1) < 1e-5 and q2 != quat
    p.keys = {0xDD}                                    # ]: wider
    p.tick[0] += 100
    F.tick()
    assert abs(p.call_slot(0x288 // 8)[3] - 0.85) < 1e-5
    # off: the game's camera again
    F.free_off()
    assert p.call_slot(0x288 // 8)[1][:3] == (1.0, 2.0, 3.0)
    # remove: the object's original vtable pointer comes back
    F.remove()
    assert struct.unpack('<Q', p.u.mem_read(CAM, 8))[0] == RDATA + 8
    # FOV / distance via curve points, restored exactly
    assert F.scale(0x6C, 1.4) == 2
    assert abs(struct.unpack('<f', p.u.mem_read(p.vps[1] + 0x6C, 4))[0] - 1.05) < 1e-6
    assert F.scale(0x6C, 1.2) == 2                     # scaling again is from the original, not compounding
    assert abs(struct.unpack('<f', p.u.mem_read(p.vps[0] + 0x6C, 4))[0] - 0.9) < 1e-6
    F.scale(0x60, 2.0)
    assert struct.unpack('<f', p.u.mem_read(p.vps[1] + 0x60, 4))[0] == 8.0
    F.restore(0x6C)
    F.restore(0x60)
    assert struct.unpack('<f', p.u.mem_read(p.vps[0] + 0x6C, 4))[0] == 0.75
    assert struct.unpack('<f', p.u.mem_read(p.vps[1] + 0x60, 4))[0] == 4.0


def test_free_camera_refuses_when_hook_not_called():
    p = Proc()
    L, F = p.lua()
    assert not F.free_on()
    assert any('not being called' in m for m in p.messages)


def test_d1_only_touches_padding():
    p = Proc()
    L, F = p.lua()
    assert F.d1_on()
    assert bytes(p.u.mem_read(0x142E68800, 16)) == b'\x90' * 16
    F.d1_off()
    assert bytes(p.u.mem_read(0x142E68800, 16)) == b'\0' * 16
    p.u.mem_write(0x142E68800, b'\x48')
    assert not F.d1_on()


if __name__ == '__main__':
    for t in (test_hook_passthrough_override_probe_curves, test_free_camera_refuses_when_hook_not_called,
              test_d1_only_touches_padding):
        t()
        print('ok', t.__name__)
