--[[ ACU free camera + FOV for AC Unity 1.5.0 on a Mac (CrossOver, Rosetta 2). Cheat Engine 7.7 (Windows build, inside
the bottle), attached to ACU.exe. NO GAME CODE IS CHANGED: on this Mac the game dies whenever it executes a modified
instruction (handoff 2026-10-12, tests 1-8), so everything here is data:

  FOV / distance  writes the current camera mode's curve points (CameraData -> HorizontalCurvePoint ->
                  VerticalCurvePoint -> PointData.fov / distanceFromPlayer), the same fields ACUFixes edits.
  Free camera     the player camera component is a C++ object; its first 8 bytes point at its vtable. We copy the
                  vtable into our own memory, point ONE slot (0x288, ApplyCameraFX(pos, quat, fov), in/out) at a small
                  hook, and swap the object's vtable pointer. The game's code bytes stay identical. The hook calls
                  the real ApplyCameraFX, records the game's camera, and when free camera is on writes ours over it.
                  Every other slot goes through a 2-instruction counter stub, so the probe can show which virtuals run.

Layouts and addresses: ACUFixes / ACU-RE (NameTaken3125), ACU 1.5.0:
  CameraManager singleton    [0x14521AAD0]; +0x40 SmallArray<ACUPlayerCameraComponent*> (size u16 at +0x4A)
  ACUPlayerCameraComponent   +0x50 positionLookFrom, +0x60 quaternion (x,y,z,w), +0x70 fov (radians),
                             +0x9B8 SharedBlock* current CameraSelectorBlenderNode, +0xA90 locationLookat
  CameraSelectorNode         +0x20 CameraData*;  CameraData +0x2F0 SmallArray<HorizontalCurvePoint*>
  HorizontalCurvePoint       +0x08 SmallArray<VerticalCurvePoint*>;  VerticalCurvePoint +0x60 distance, +0x6C fov
Hook machine code: assembled and disassembled with GNU as / objdump (acu_camera/fx.s); see README.
]]

acufc = acufc or {}
local F = acufc
F.CAMMGR = 0x14521AAD0
F.SLOT_FX = 0x288 // 8          -- 81
F.NSLOTS = 128
-- hook body: offsets 0x800 orig, 0x808 on, 0x810 calls, 0x820 pos, 0x830 quat, 0x840 fov, 0x850 gpos, 0x860 gquat, 0x870 gfov
F.FX_HEX = '53565741544883ec284889d64c89c74d89ccff15e8070000f048ff05f00700000f10060f1105260800000f10070f11052c080000' ..
           '418b0424890532080000833dc307000000741e0f1005d20700000f11060f1005d80700000f11078b05df070000418904244883c4' ..
           '28415c5f5e5bc3'
local O = {orig = 0x800, on = 0x808, calls = 0x810, pos = 0x820, quat = 0x830, fov = 0x840,
           gpos = 0x850, gquat = 0x860, gfov = 0x870, vt = 0x1000, stubs = 0x1800, cnt = 0x3000, origs = 0x3800}

local function hexbytes(h)
  local t = {}
  for i = 1, #h, 2 do t[#t + 1] = tonumber(h:sub(i, i + 1), 16) end
  return t
end

local function le32(v)
  if v < 0 then v = v + 0x100000000 end
  return {v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >> 24) & 0xff}
end

function F.cam()
  local mgr = readQword(F.CAMMGR)
  if not mgr or mgr == 0 then return nil end
  local arr, n = readQword(mgr + 0x40), readSmallInteger(mgr + 0x4A)
  if not arr or arr == 0 or not n or n == 0 then return nil end
  local c = readQword(arr)
  if not c or c == 0 then return nil end
  return c
end

-- ------------------------------------------------------------------------------------------- hook install / remove
function F.install()
  local cam = F.cam()
  if not cam then showMessage('No player camera yet: load a save first.') return false end
  if F.mem == nil then
    F.mem = allocateMemory(0x4000)
    writeBytes(F.mem, hexbytes(F.FX_HEX))
    registerSymbol('acufc_mem', F.mem)
  end
  local m = F.mem
  local vptr = readQword(cam)
  if vptr == m + O.vt + 8 then return true end        -- already ours
  F.cam_obj, F.vptr = cam, vptr
  writeQword(m + O.vt, readQword(vptr - 8))           -- RTTI locator slot, kept as is
  for i = 0, F.NSLOTS - 1 do
    local fn = readQword(vptr + 8 * i) or 0
    writeQword(m + O.origs + 8 * i, fn)
    local s = m + O.stubs + 0x20 * i
    local b = {0xF0, 0x48, 0xFF, 0x05}
    for _, x in ipairs(le32((O.cnt + 8 * i) - (O.stubs + 0x20 * i + 8))) do b[#b + 1] = x end
    b[#b + 1] = 0xFF; b[#b + 1] = 0x25
    for _, x in ipairs(le32((O.origs + 8 * i) - (O.stubs + 0x20 * i + 14))) do b[#b + 1] = x end
    writeBytes(s, b)
    writeQword(m + O.vt + 8 + 8 * i, s)
  end
  writeQword(m + O.orig, readQword(vptr + 8 * F.SLOT_FX))
  writeQword(m + O.vt + 8 + 8 * F.SLOT_FX, m)         -- slot 0x288 -> the camera hook
  writeQword(cam, m + O.vt + 8)                       -- the swap: one 8-byte data write
  return true
end

function F.remove()
  F.free_off()
  if F.cam_obj and F.vptr and readQword(F.cam_obj) == F.mem + O.vt + 8 then writeQword(F.cam_obj, F.vptr) end
  F.cam_obj = nil
end

function F.calls() return F.mem and readQword(F.mem + O.calls) or 0 end

-- which virtuals run: counts per slot over `sec` seconds
function F.probe(sec)
  sec = sec or 2
  if not F.install() then return end
  local a = {}
  for i = 0, F.NSLOTS - 1 do a[i] = readQword(F.mem + O.cnt + 8 * i) end
  local c0 = F.calls()
  sleep(sec * 1000)
  local out = {}
  for i = 0, F.NSLOTS - 1 do
    local d = readQword(F.mem + O.cnt + 8 * i) - a[i]
    if d > 0 then out[#out + 1] = string.format('slot 0x%03X: %.0f/s', 8 * i, d / sec) end
  end
  out[#out + 1] = string.format('slot 0x288 ApplyCameraFX (hook): %.0f/s', (F.calls() - c0) / sec)
  print('Virtuals called on the player camera:\n' .. table.concat(out, '\n'))
  return out
end

-- ------------------------------------------------------------------------------------------- quaternion helpers (x,y,z,w)
local function qmul(a, b)
  return {a[4]*b[1] + a[1]*b[4] + a[2]*b[3] - a[3]*b[2],
          a[4]*b[2] - a[1]*b[3] + a[2]*b[4] + a[3]*b[1],
          a[4]*b[3] + a[1]*b[2] - a[2]*b[1] + a[3]*b[4],
          a[4]*b[4] - a[1]*b[1] - a[2]*b[2] - a[3]*b[3]}
end
local function qaxis(ax, ang)
  local s = math.sin(ang / 2)
  return {ax[1]*s, ax[2]*s, ax[3]*s, math.cos(ang / 2)}
end
local function qnorm(q)
  local n = math.sqrt(q[1]^2 + q[2]^2 + q[3]^2 + q[4]^2)
  if n < 1e-9 then return {0, 0, 0, 1} end
  return {q[1]/n, q[2]/n, q[3]/n, q[4]/n}
end
local function qrot(q, v)
  local r = qmul(qmul(q, {v[1], v[2], v[3], 0}), {-q[1], -q[2], -q[3], q[4]})
  return {r[1], r[2], r[3]}
end
local function dot(a, b) return a[1]*b[1] + a[2]*b[2] + a[3]*b[3] end
local function cross(a, b) return {a[2]*b[3]-a[3]*b[2], a[3]*b[1]-a[1]*b[3], a[1]*b[2]-a[2]*b[1]} end
local function vnorm(v) local n = math.sqrt(dot(v, v)); if n < 1e-9 then return {0, 0, 0} end return {v[1]/n, v[2]/n, v[3]/n} end
local function rd4(a) return {readFloat(a), readFloat(a + 4), readFloat(a + 8), readFloat(a + 12)} end

-- ------------------------------------------------------------------------------------------- free camera
F.mirror = F.mirror or false
F.speed, F.turn, F.fovrate = 3.0, math.rad(60), 0.5

local function write_state()
  local b = {}
  for _, v in ipairs({F.p[1], F.p[2], F.p[3], 1.0, F.q[1], F.q[2], F.q[3], F.q[4]}) do
    for _, x in ipairs(floatToByteTable(v)) do b[#b + 1] = x end
  end
  writeBytes(F.mem + O.pos, b)
  writeFloat(F.mem + O.fov, F.f)
end

function F.free_on()
  if not F.install() then return false end
  if F.calls() == 0 then
    sleep(500)
    if F.calls() == 0 then
      showMessage('The camera hook is not being called (0 calls). Free camera stays off.\n' ..
                  'Run "Probe: which camera virtuals run" and send the output to Claude.')
      return false
    end
  end
  F.p = rd4(F.mem + O.gpos)
  F.q = qnorm(rd4(F.mem + O.gquat))
  F.f = readFloat(F.mem + O.gfov)
  -- find the camera's local forward axis: the rotated basis axis that points from the camera to its look-at point
  local cam = F.cam()
  local look = cam and rd4(cam + 0xA90)
  local fw = look and vnorm({look[1]-F.p[1], look[2]-F.p[2], look[3]-F.p[3]})
  F.fwd_local = {0, 1, 0}
  if fw and dot(fw, fw) > 0.5 then
    local best = -2
    for _, ax in ipairs({{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}}) do
      local d = dot(qrot(F.q, ax), fw)
      if d > best then best, F.fwd_local = d, ax end
    end
  end
  write_state()
  writeInteger(F.mem + O.on, 1)
  F.last = getTickCount()
  if not F.timer then
    F.timer = createTimer(nil, false)
    F.timer.Interval = 15
    F.timer.OnTimer = function() F.tick() end
  end
  F.timer.Enabled = true
  return true
end

function F.free_off()
  if F.timer then F.timer.Enabled = false end
  if F.mem then writeInteger(F.mem + O.on, 0) end
end

local K = function(c) return isKeyPressed(type(c) == 'string' and string.byte(c) or c) end

function F.tick()
  local now = getTickCount()
  local dt = math.min((now - F.last) / 1000, 0.1)
  F.last = now
  if not F.cam_obj or readQword(F.cam_obj) ~= F.mem + O.vt + 8 then   -- camera object replaced (load, cutscene)
    F.free_off()
    return
  end
  local mul = K(0x10) and 5 or (K(0x11) and 0.2 or 1)                   -- Shift fast, Ctrl slow
  local Z = {0, 0, 1}
  local fwd = vnorm(qrot(F.q, F.fwd_local))
  local right = vnorm(cross(fwd, Z))
  if F.mirror then right = {-right[1], -right[2], -right[3]} end
  local mv, s = {0, 0, 0}, F.speed * mul * dt
  local function add(v, k) mv = {mv[1] + v[1]*k, mv[2] + v[2]*k, mv[3] + v[3]*k} end
  if K('I') then add(fwd, s) end
  if K('K') then add(fwd, -s) end
  if K('L') then add(right, s) end
  if K('J') then add(right, -s) end
  if K('O') then add(Z, s) end
  if K('U') then add(Z, -s) end
  F.p = {F.p[1] + mv[1], F.p[2] + mv[2], F.p[3] + mv[3]}
  local a = F.turn * dt * (K(0x11) and 0.25 or 1)
  local yaw = (K(0x25) and 1 or 0) - (K(0x27) and 1 or 0)               -- Left / Right arrows
  if F.mirror then yaw = -yaw end
  local pitch = (K(0x26) and 1 or 0) - (K(0x28) and 1 or 0)             -- Up / Down arrows
  local roll = (K(0xBE) and 1 or 0) - (K(0xBC) and 1 or 0)              -- . / ,
  if yaw ~= 0 then F.q = qmul(qaxis(Z, yaw * a), F.q) end
  if pitch ~= 0 and dot(right, right) > 0.5 then F.q = qmul(qaxis(right, pitch * a), F.q) end
  if roll ~= 0 then F.q = qmul(qaxis(fwd, roll * a * 0.5), F.q) end
  F.q = qnorm(F.q)
  local df = (K(0xDD) and 1 or 0) - (K(0xDB) and 1 or 0)                -- ] wider, [ narrower
  if df ~= 0 then F.f = math.max(0.05, math.min(2.6, F.f + df * F.fovrate * dt)) end
  write_state()
end

-- ------------------------------------------------------------------------------------------- FOV / distance (data only)
function F.curve_points()
  local cam = F.cam()
  if not cam then return {} end
  local sb = readQword(cam + 0x9B8)
  if not sb or sb == 0 then return {} end
  local flags = readInteger(sb + 0xC)
  if not flags or (flags & 0x80000000) == 0 then return {} end
  local node = readQword(sb)
  local cd = node and readQword(node + 0x20)
  if not cd or cd == 0 then return {} end
  local out = {}
  local harr, hn = readQword(cd + 0x2F0), readSmallInteger(cd + 0x2FA)
  for i = 0, (hn or 0) - 1 do
    local hp = readQword(harr + 8 * i)
    local varr, vn = readQword(hp + 0x08), readSmallInteger(hp + 0x12)
    for j = 0, (vn or 0) - 1 do out[#out + 1] = readQword(varr + 8 * j) end
  end
  return out
end

F.saved = F.saved or {}          -- F.saved[field][address] = original float
function F.scale(field, k)       -- field 0x6C fov, 0x60 distance
  F.saved[field] = F.saved[field] or {}
  local S, n = F.saved[field], 0
  for _, vp in ipairs(F.curve_points()) do
    local a = vp + field
    if S[a] == nil then S[a] = readFloat(a) end
    writeFloat(a, S[a] * k)
    n = n + 1
  end
  return n
end
function F.restore(field)
  for a, v in pairs(F.saved[field] or {}) do writeFloat(a, v) end
  F.saved[field] = nil
end

-- ------------------------------------------------------------------------------------------- diagnostic D1
-- Changes 16 bytes that are never executed (the unused end of .text used as a cave in test 6), with no jump to them.
-- Survives 2 minutes of play -> nothing is checksumming the code; the crashes come from EXECUTING changed code
-- (Rosetta / Wine). Crashes -> a second integrity check scans .text; code patching needs that found first.
F.D1 = 0x140000000 + 0x2E68800
function F.d1_on()
  local b = readBytes(F.D1, 16, true)
  for _, x in ipairs(b) do
    if x ~= 0 and x ~= 0xCC then showMessage('D1: bytes there are not padding; not touching them.') return false end
  end
  F.d1_saved = b
  local t = {}
  for i = 1, 16 do t[i] = 0x90 end
  writeBytes(F.D1, t)
  return true
end
function F.d1_off() if F.d1_saved then writeBytes(F.D1, F.d1_saved) F.d1_saved = nil end end

return F
