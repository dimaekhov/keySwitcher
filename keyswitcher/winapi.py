from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import logging
import sys
import time
from typing import Callable

from .language import Language

if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
else:
    user32 = None
    kernel32 = None

WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_INPUTLANGCHANGEREQUEST = 0x0050

LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_PAUSE = 0x13
VK_CAPITAL = 0x14
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_DELETE = 0x2E
VK_C = 0x43
VK_LWIN = 0x5B
VK_RWIN = 0x5C

KLF_ACTIVATE = 0x00000001

EN_KLID = "00000409"
RU_KLID = "00000419"
EN_PRIMARY_LANG = 0x09
RU_PRIMARY_LANG = 0x19

ULONG_PTR = wintypes.WPARAM
HOOK_CALLBACK = Callable[["KeyboardEvent"], bool]
LOGGER = logging.getLogger("keyswitcher.winapi")


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    # SendInput validates cbSize against the native INPUT size. On x64 that size
    # is determined by MOUSEINPUT, not KEYBDINPUT, so the union must include all
    # variants even though this app only sends keyboard input.
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


if sys.platform == "win32":
    LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
        wintypes.LPARAM,
        ctypes.c_int,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int,
        LowLevelKeyboardProc,
        wintypes.HINSTANCE,
        wintypes.DWORD,
    ]
    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.CallNextHookEx.argtypes = [
        wintypes.HHOOK,
        ctypes.c_int,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.CallNextHookEx.restype = wintypes.LPARAM
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [
        ctypes.POINTER(MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.GetMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.GetKeyboardState.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
    user32.GetKeyboardState.restype = wintypes.BOOL
    user32.GetKeyState.argtypes = [ctypes.c_int]
    user32.GetKeyState.restype = wintypes.SHORT
    user32.ToUnicodeEx.argtypes = [
        wintypes.UINT,
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_ubyte),
        wintypes.LPWSTR,
        ctypes.c_int,
        wintypes.UINT,
        wintypes.HKL,
    ]
    user32.ToUnicodeEx.restype = ctypes.c_int
    user32.LoadKeyboardLayoutW.argtypes = [wintypes.LPCWSTR, wintypes.UINT]
    user32.LoadKeyboardLayoutW.restype = wintypes.HKL
    user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
    user32.GetKeyboardLayout.restype = wintypes.HKL
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
    user32.GetGUIThreadInfo.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.ActivateKeyboardLayout.argtypes = [wintypes.HKL, wintypes.UINT]
    user32.ActivateKeyboardLayout.restype = wintypes.HKL
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = wintypes.SHORT
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.GetClipboardSequenceNumber.restype = wintypes.DWORD

    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL


@dataclass(slots=True)
class KeyboardEvent:
    vk_code: int
    scan_code: int
    flags: int
    message: int

    @property
    def is_key_down(self) -> bool:
        return self.message in {WM_KEYDOWN, WM_SYSKEYDOWN}

    @property
    def is_key_up(self) -> bool:
        return self.message in {WM_KEYUP, WM_SYSKEYUP}

    @property
    def injected(self) -> bool:
        return bool(self.flags & LLKHF_INJECTED)


@dataclass(slots=True)
class ClipboardSelection:
    text: str
    previous_text: str | None


def ensure_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("KeySwitcher works only on Windows.")


def _raise_last_error(action: str) -> None:
    error = ctypes.get_last_error()
    raise OSError(error, f"{action} failed with Win32 error {error}")


class KeyboardHook:
    def __init__(self, callback: HOOK_CALLBACK) -> None:
        ensure_windows()
        self._callback = callback
        self._hook: wintypes.HHOOK | None = None
        self._proc = LowLevelKeyboardProc(self._handle)

    def install(self) -> None:
        module_handle = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, module_handle, 0)
        if not self._hook:
            _raise_last_error("SetWindowsHookExW")

    def uninstall(self) -> None:
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def run_message_loop(self) -> None:
        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self) -> None:
        user32.PostQuitMessage(0)

    def _handle(self, code: int, w_param: int, l_param: int) -> int:
        block = False
        if code == HC_ACTION:
            raw = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            event = KeyboardEvent(
                vk_code=int(raw.vkCode),
                scan_code=int(raw.scanCode),
                flags=int(raw.flags),
                message=int(w_param),
            )
            if not event.injected:
                try:
                    block = self._callback(event)
                except Exception:
                    LOGGER.exception("Keyboard hook callback failed")
                    block = False
        if block:
            return 1
        return user32.CallNextHookEx(self._hook, code, w_param, l_param)


class LayoutManager:
    def __init__(self) -> None:
        ensure_windows()
        self._layouts: dict[Language, int] = {
            "en": int(user32.LoadKeyboardLayoutW(EN_KLID, 0)),
            "ru": int(user32.LoadKeyboardLayoutW(RU_KLID, 0)),
        }
        if not self._layouts["en"] or not self._layouts["ru"]:
            _raise_last_error("LoadKeyboardLayoutW")

    def foreground_language(self) -> Language:
        hwnd = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(hwnd, None) if hwnd else 0
        hkl = int(user32.GetKeyboardLayout(thread_id))
        return self.language_from_hkl(hkl)

    def target_layout(self, language: Language) -> int:
        return self._layouts[language]

    def switch_foreground_layout(self, language: Language) -> None:
        hwnd = self._foreground_focus_window()
        if not hwnd:
            return
        hkl = self.target_layout(language)
        user32.ActivateKeyboardLayout(hkl, 0)
        user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, hkl)

    @staticmethod
    def language_from_hkl(hkl: int) -> Language:
        lang_id = hkl & 0xFFFF
        primary = lang_id & 0x03FF
        if primary == RU_PRIMARY_LANG:
            return "ru"
        if primary == EN_PRIMARY_LANG:
            return "en"
        return "en"

    @staticmethod
    def _foreground_focus_window() -> int:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return 0
        thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        info = GUITHREADINFO()
        info.cbSize = ctypes.sizeof(GUITHREADINFO)
        if user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)) and info.hwndFocus:
            return int(info.hwndFocus)
        return int(hwnd)


class KeyboardTranslator:
    def __init__(self, layouts: LayoutManager) -> None:
        self._layouts = layouts

    def char_for_event(self, event: KeyboardEvent, language: Language) -> str:
        if _command_modifier_down():
            return ""
        state = (ctypes.c_ubyte * 256)()
        if not user32.GetKeyboardState(state):
            return ""
        state[event.vk_code] |= 0x80
        buffer = ctypes.create_unicode_buffer(8)
        scan = event.scan_code
        if event.flags & LLKHF_EXTENDED:
            scan |= 0xE000
        result = user32.ToUnicodeEx(
            event.vk_code,
            scan,
            state,
            buffer,
            len(buffer),
            0,
            self._layouts.target_layout(language),
        )
        if result < 0:
            user32.ToUnicodeEx(
                event.vk_code,
                scan,
                state,
                buffer,
                len(buffer),
                0,
                self._layouts.target_layout(language),
            )
            return ""
        if result == 0:
            return ""
        return buffer.value[:result]


def _command_modifier_down() -> bool:
    for vk_code in (VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN):
        if user32.GetAsyncKeyState(vk_code) & 0x8000:
            return True
    return False


def is_shift_down() -> bool:
    return bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)


def is_navigation_key(vk_code: int) -> bool:
    return vk_code in {
        VK_ESCAPE,
        VK_PRIOR,
        VK_NEXT,
        VK_END,
        VK_HOME,
        VK_LEFT,
        VK_UP,
        VK_RIGHT,
        VK_DOWN,
        VK_DELETE,
        VK_PAUSE,
    }


def send_backspaces(count: int) -> None:
    if count <= 0:
        return
    events: list[INPUT] = []
    for _ in range(count):
        events.append(_vk_input(VK_BACK, False))
        events.append(_vk_input(VK_BACK, True))
    _send_inputs(events)


def send_text(text: str) -> None:
    events: list[INPUT] = []
    utf16 = text.encode("utf-16-le")
    for index in range(0, len(utf16), 2):
        code_unit = int.from_bytes(utf16[index : index + 2], "little")
        events.append(_unicode_input(code_unit, False))
        events.append(_unicode_input(code_unit, True))
    _send_inputs(events)


def copy_selected_text(wait_ms: int = 180) -> ClipboardSelection | None:
    previous_text = get_clipboard_text()
    previous_sequence = clipboard_sequence_number()
    send_copy_shortcut()

    copied_text: str | None = None
    deadline = time.monotonic() + wait_ms / 1000
    while time.monotonic() <= deadline:
        if previous_sequence and clipboard_sequence_number() != previous_sequence:
            copied_text = get_clipboard_text()
            break
        time.sleep(0.01)

    if copied_text is None and previous_sequence == 0:
        current_text = get_clipboard_text()
        if current_text != previous_text:
            copied_text = current_text

    if copied_text is None:
        return None
    return ClipboardSelection(copied_text, previous_text)


def restore_clipboard_text(text: str | None) -> None:
    if text is None:
        return

    encoded = (text + "\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(encoded))
    if not handle:
        _raise_last_error("GlobalAlloc")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        _raise_last_error("GlobalLock")
    try:
        ctypes.memmove(pointer, encoded, len(encoded))
    finally:
        kernel32.GlobalUnlock(handle)

    try:
        if not _open_clipboard():
            _raise_last_error("OpenClipboard")
        try:
            if not user32.EmptyClipboard():
                _raise_last_error("EmptyClipboard")
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                _raise_last_error("SetClipboardData")
            handle = None
        finally:
            user32.CloseClipboard()
    finally:
        if handle:
            kernel32.GlobalFree(handle)


def get_clipboard_text() -> str | None:
    if not _open_clipboard():
        return None
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return None
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def clipboard_sequence_number() -> int:
    return int(user32.GetClipboardSequenceNumber())


def send_copy_shortcut() -> None:
    shift_was_down = is_shift_down()
    events: list[INPUT] = []
    if shift_was_down:
        events.append(_vk_input(VK_SHIFT, True))
    events.extend(
        [
            _vk_input(VK_CONTROL, False),
            _vk_input(VK_C, False),
            _vk_input(VK_C, True),
            _vk_input(VK_CONTROL, True),
        ]
    )
    if shift_was_down:
        events.append(_vk_input(VK_SHIFT, False))
    _send_inputs(events)


def _open_clipboard(retries: int = 8) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(0):
            return True
        time.sleep(0.01)
    return False


def _vk_input(vk_code: int, key_up: bool) -> INPUT:
    flags = KEYEVENTF_KEYUP if key_up else 0
    item = INPUT()
    item.type = INPUT_KEYBOARD
    item.union.ki = KEYBDINPUT(vk_code, 0, flags, 0, 0)
    return item


def _unicode_input(code_unit: int, key_up: bool) -> INPUT:
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if key_up else 0)
    item = INPUT()
    item.type = INPUT_KEYBOARD
    item.union.ki = KEYBDINPUT(0, code_unit, flags, 0, 0)
    return item


def _send_inputs(events: list[INPUT]) -> None:
    if not events:
        return
    array_type = INPUT * len(events)
    sent = user32.SendInput(len(events), array_type(*events), ctypes.sizeof(INPUT))
    if sent != len(events):
        _raise_last_error("SendInput")
