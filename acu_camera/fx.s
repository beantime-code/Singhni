.intel_syntax noprefix
.text
base:
fx_hook:
  push rbx
  push rsi
  push rdi
  push r12
  sub rsp, 0x28
  mov rsi, rdx
  mov rdi, r8
  mov r12, r9
  call qword ptr [rip + orig_fx]
  lock inc qword ptr [rip + calls]
  movups xmm0, [rsi]
  movups [rip + gpos], xmm0
  movups xmm0, [rdi]
  movups [rip + gquat], xmm0
  mov eax, [r12]
  mov [rip + gfov], eax
  cmp dword ptr [rip + on], 0
  je done
  movups xmm0, [rip + pos]
  movups [rsi], xmm0
  movups xmm0, [rip + quat]
  movups [rdi], xmm0
  mov eax, [rip + fov]
  mov [r12], eax
done:
  add rsp, 0x28
  pop r12
  pop rdi
  pop rsi
  pop rbx
  ret
.org 0x800
orig_fx: .quad 0
on:      .long 0, 0
calls:   .quad 0
.org 0x820
pos:  .long 0,0,0,0
quat: .long 0,0,0,0
fov:  .long 0
.org 0x850
gpos:  .long 0,0,0,0
gquat: .long 0,0,0,0
gfov:  .long 0
