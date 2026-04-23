from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import logging
import sys
from typing import Callable

from .config import AppConfig
from .language import Language

if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
else:
    user32 = None
    kernel32 = None
    shell32 = None
    gdi32 = None

LOGGER = logging.getLogger("keyswitcher.ui")

HINT_LABELS = {
    "active": "активно",
    "paused": "пауза",
    "startup error": "ошибка автозапуска",
    "startup on": "автозапуск вкл",
    "startup off": "автозапуск выкл",
    "rules": "правила",
    "layout": "раскладка",
}

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_TIMER = 0x0113
WM_PAINT = 0x000F
WM_MOVE = 0x0003
WM_SIZE = 0x0005
WM_CONTEXTMENU = 0x007B
WM_NCHITTEST = 0x0084
WM_EXITSIZEMOVE = 0x0232
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TRANSPARENT = 0x00000020

SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = wintypes.HWND(-1)

LWA_ALPHA = 0x00000002

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTBUTTON = 0x0002

DT_CENTER = 0x00000001
DT_VCENTER = 0x00000004
DT_SINGLELINE = 0x00000020
DT_NOPREFIX = 0x00000800
DT_END_ELLIPSIS = 0x00008000
DT_LEFT = 0x00000000

TRANSPARENT = 1
FW_BOLD = 700
FW_SEMIBOLD = 600
DEFAULT_CHARSET = 1
OUT_DEFAULT_PRECIS = 0
CLIP_DEFAULT_PRECIS = 0
DEFAULT_QUALITY = 0
DEFAULT_PITCH = 0

SM_CXSCREEN = 0
SM_CYSCREEN = 1

HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

ID_TRAY_TOGGLE = 1001
ID_TRAY_EXIT = 1002
ID_TRAY_EDIT_RULES = 1003
ID_TRAY_RELOAD_RULES = 1004
ID_TRAY_STARTUP = 1005
ID_TRAY_DEBUG_LOG = 1006
HINT_TIMER_ID = 2001
TRAY_POLL_TIMER_ID = 2002


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


class WNDCLASSEXW(ctypes.Structure):
    pass


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
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


if sys.platform == "win32":
    WNDPROC = ctypes.WINFUNCTYPE(
        wintypes.LPARAM,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    WNDCLASSEXW._fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]

    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL

    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        wintypes.LPVOID,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.DestroyWindow.restype = wintypes.BOOL
    user32.DefWindowProcW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.DefWindowProcW.restype = wintypes.LPARAM
    user32.CreatePopupMenu.restype = wintypes.HMENU
    user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.WPARAM, wintypes.LPCWSTR]
    user32.AppendMenuW.restype = wintypes.BOOL
    user32.TrackPopupMenu.argtypes = [
        wintypes.HMENU,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.LPVOID,
    ]
    user32.TrackPopupMenu.restype = wintypes.BOOL
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
    user32.GetGUIThreadInfo.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.SetLayeredWindowAttributes.argtypes = [
        wintypes.HWND,
        wintypes.COLORREF,
        ctypes.c_ubyte,
        wintypes.DWORD,
    ]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT), wintypes.BOOL]
    user32.UpdateWindow.argtypes = [wintypes.HWND]
    user32.SetTimer.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.LPVOID]
    user32.SetTimer.restype = wintypes.UINT
    user32.KillTimer.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
    user32.BeginPaint.restype = wintypes.HDC
    user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL

    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.UINT, wintypes.LPVOID]
    gdi32.CreateBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
    gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
    gdi32.CreateFontW.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPCWSTR,
    ]
    gdi32.CreateFontW.restype = wintypes.HFONT
    user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
    user32.FillRect.restype = ctypes.c_int
    gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
    user32.DrawTextW.argtypes = [
        wintypes.HDC,
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(wintypes.RECT),
        wintypes.UINT,
    ]
    user32.DrawTextW.restype = ctypes.c_int
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
    user32.CreateIconIndirect.restype = wintypes.HICON


@dataclass(slots=True)
class UiStatus:
    language: Language
    enabled: bool


@dataclass(slots=True)
class DebugLogEntry:
    badge: str
    line: str
    badge_bg: int
    badge_fg: int


class KeySwitcherUI:
    def __init__(
        self,
        config: AppConfig,
        initial_language: Language,
        on_toggle: Callable[[], None],
        on_toggle_startup: Callable[[], None],
        is_startup_enabled: Callable[[], bool],
        on_exit: Callable[[], None],
        on_edit_rules: Callable[[], None],
        on_reload_rules: Callable[[], None],
        on_toggle_debug_log: Callable[[], bool] | None = None,
        on_poll: Callable[[], None] | None = None,
    ) -> None:
        self._config = config
        self._status = UiStatus(initial_language, True)
        self._tray = (
            TrayIcon(
                on_toggle,
                on_toggle_startup,
                is_startup_enabled,
                on_exit,
                on_edit_rules,
                on_reload_rules,
                on_toggle_debug_log,
                on_poll,
            )
            if config.tray_icon
            else None
        )
        self._hint = SwitchHint(config.hint_duration_ms, config.hint_opacity) if config.switch_hint else None
        self._debug_overlay = DebugLogOverlay() if config.tray_icon else None

    def show(self) -> None:
        if self._tray:
            self._tray.add(self._status)

    def close(self) -> None:
        if self._tray:
            self._tray.close()
        if self._hint:
            self._hint.close()
        if self._debug_overlay:
            self._debug_overlay.close()

    def set_status(self, language: Language, enabled: bool) -> None:
        if self._status.language == language and self._status.enabled == enabled:
            return
        self._status = UiStatus(language, enabled)
        if self._tray:
            self._tray.update(self._status)

    def show_switch_hint(self, language: Language, replacement: str) -> None:
        if self._hint:
            self._hint.show(language, replacement)

    def show_state_hint(self, enabled: bool) -> None:
        if self._hint:
            self._hint.show(self._status.language, "active" if enabled else "paused", enabled=enabled)

    def set_debug_log_visible(self, visible: bool) -> None:
        if self._tray:
            self._tray.set_debug_log_visible(visible)
        if self._debug_overlay:
            self._debug_overlay.set_visible(visible)

    def append_debug_log(self, line: str) -> None:
        if self._debug_overlay:
            self._debug_overlay.append(line)

    def debug_log_visible(self) -> bool:
        return self._debug_overlay.visible() if self._debug_overlay else False


class TrayIcon:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_toggle_startup: Callable[[], None],
        is_startup_enabled: Callable[[], bool],
        on_exit: Callable[[], None],
        on_edit_rules: Callable[[], None],
        on_reload_rules: Callable[[], None],
        on_toggle_debug_log: Callable[[], bool] | None = None,
        on_poll: Callable[[], None] | None = None,
    ) -> None:
        self._on_toggle = on_toggle
        self._on_toggle_startup = on_toggle_startup
        self._is_startup_enabled = is_startup_enabled
        self._on_exit = on_exit
        self._on_edit_rules = on_edit_rules
        self._on_reload_rules = on_reload_rules
        self._on_toggle_debug_log = on_toggle_debug_log
        self._on_poll = on_poll
        self._class_name = "KeySwitcherTrayWindow"
        self._hwnd: int = 0
        self._icon: int = 0
        self._added = False
        self._status = UiStatus("en", True)
        self._debug_log_visible = False
        self._wndproc = WNDPROC(self._window_proc)
        self._create_window()

    def add(self, status: UiStatus) -> None:
        self._status = status
        self._replace_icon(_create_badge_icon(status))
        data = self._notify_data(NIF_MESSAGE | NIF_ICON | NIF_TIP)
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data)):
            LOGGER.warning("Shell_NotifyIconW(NIM_ADD) failed: %s", ctypes.get_last_error())
            return
        self._added = True
        if self._on_poll:
            user32.SetTimer(self._hwnd, TRAY_POLL_TIMER_ID, 1000, None)

    def update(self, status: UiStatus) -> None:
        self._status = status
        self._replace_icon(_create_badge_icon(status))
        if not self._added:
            self.add(status)
            return
        data = self._notify_data(NIF_ICON | NIF_TIP)
        if not shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data)):
            LOGGER.warning("Shell_NotifyIconW(NIM_MODIFY) failed: %s", ctypes.get_last_error())

    def close(self) -> None:
        if self._hwnd:
            user32.KillTimer(self._hwnd, TRAY_POLL_TIMER_ID)
        if self._added:
            data = self._notify_data(0)
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
            self._added = False
        if self._icon:
            user32.DestroyIcon(self._icon)
            self._icon = 0
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = 0

    def _create_window(self) -> None:
        hinstance = kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSEXW()
        window_class.cbSize = ctypes.sizeof(WNDCLASSEXW)
        window_class.lpfnWndProc = self._wndproc
        window_class.hInstance = hinstance
        window_class.lpszClassName = self._class_name
        atom = user32.RegisterClassExW(ctypes.byref(window_class))
        if not atom and ctypes.get_last_error() != 1410:
            raise ctypes.WinError(ctypes.get_last_error())
        hwnd = user32.CreateWindowExW(
            0,
            self._class_name,
            "KeySwitcher",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self._hwnd = int(hwnd)

    def _notify_data(self, flags: int) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = 1
        data.uFlags = flags
        data.uCallbackMessage = WM_TRAYICON
        data.hIcon = self._icon
        data.szTip = _tooltip(self._status)[:127]
        return data

    def _replace_icon(self, icon: int) -> None:
        previous = self._icon
        self._icon = icon
        if previous:
            user32.DestroyIcon(previous)

    def set_debug_log_visible(self, visible: bool) -> None:
        self._debug_log_visible = visible

    def _window_proc(self, hwnd: int, msg: int, w_param: int, l_param: int) -> int:
        try:
            if msg == WM_TRAYICON:
                if l_param == WM_LBUTTONUP:
                    self._on_toggle()
                    return 0
                if l_param in {WM_RBUTTONUP, WM_CONTEXTMENU}:
                    self._show_menu()
                    return 0
            if msg == WM_COMMAND:
                command_id = w_param & 0xFFFF
                if command_id == ID_TRAY_TOGGLE:
                    self._on_toggle()
                    return 0
                if command_id == ID_TRAY_EDIT_RULES:
                    self._on_edit_rules()
                    return 0
                if command_id == ID_TRAY_RELOAD_RULES:
                    self._on_reload_rules()
                    return 0
                if command_id == ID_TRAY_STARTUP:
                    self._on_toggle_startup()
                    return 0
                if command_id == ID_TRAY_DEBUG_LOG:
                    if self._on_toggle_debug_log:
                        self._debug_log_visible = self._on_toggle_debug_log()
                    return 0
                if command_id == ID_TRAY_EXIT:
                    self._on_exit()
                    return 0
            if msg == WM_TIMER and w_param == TRAY_POLL_TIMER_ID:
                if self._on_poll:
                    self._on_poll()
                return 0
        except Exception:
            LOGGER.exception("Tray window procedure failed")
        return user32.DefWindowProcW(hwnd, msg, w_param, l_param)

    def _show_menu(self) -> None:
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        try:
            toggle_label = "Поставить KeySwitcher на паузу" if self._status.enabled else "Возобновить KeySwitcher"
            startup_label = "Отключить автозапуск Windows" if self._is_startup_enabled() else "Запускать вместе с Windows"
            debug_log_label = "Скрыть журнал отладки" if self._debug_log_visible else "Показать журнал отладки"
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_TOGGLE, toggle_label)
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_EDIT_RULES, "Изменить правила...")
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_RELOAD_RULES, "Перезагрузить правила")
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_DEBUG_LOG, debug_log_label)
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_STARTUP, startup_label)
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_EXIT, "Выход")
            point = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(point))
            user32.SetForegroundWindow(self._hwnd)
            user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON, point.x, point.y, 0, self._hwnd, None)
        finally:
            user32.DestroyMenu(menu)


class SwitchHint:
    def __init__(self, duration_ms: int, opacity: int) -> None:
        self._class_name = "KeySwitcherHintWindow"
        self._duration_ms = max(250, int(duration_ms))
        self._opacity = max(80, min(255, int(opacity)))
        self._language: Language = "en"
        self._text = ""
        self._enabled = True
        self._hwnd: int = 0
        self._wndproc = WNDPROC(self._window_proc)
        self._create_window()

    def show(self, language: Language, text: str, enabled: bool = True) -> None:
        self._language = language
        self._text = _hint_text(text)[:32]
        self._enabled = enabled
        width = max(116, min(310, 74 + len(self._text) * 9))
        height = 54
        x, y = _hint_position(width, height)
        user32.SetLayeredWindowAttributes(self._hwnd, 0, self._opacity, LWA_ALPHA)
        user32.SetWindowPos(
            self._hwnd,
            HWND_TOPMOST,
            x,
            y,
            width,
            height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        user32.ShowWindow(self._hwnd, SW_SHOWNOACTIVATE)
        user32.InvalidateRect(self._hwnd, None, True)
        user32.UpdateWindow(self._hwnd)
        user32.KillTimer(self._hwnd, HINT_TIMER_ID)
        user32.SetTimer(self._hwnd, HINT_TIMER_ID, self._duration_ms, None)

    def close(self) -> None:
        if self._hwnd:
            user32.KillTimer(self._hwnd, HINT_TIMER_ID)
            user32.DestroyWindow(self._hwnd)
            self._hwnd = 0

    def _create_window(self) -> None:
        hinstance = kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSEXW()
        window_class.cbSize = ctypes.sizeof(WNDCLASSEXW)
        window_class.lpfnWndProc = self._wndproc
        window_class.hInstance = hinstance
        window_class.lpszClassName = self._class_name
        atom = user32.RegisterClassExW(ctypes.byref(window_class))
        if not atom and ctypes.get_last_error() != 1410:
            raise ctypes.WinError(ctypes.get_last_error())
        hwnd = user32.CreateWindowExW(
            WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT,
            self._class_name,
            "Подсказка KeySwitcher",
            WS_POPUP,
            0,
            0,
            120,
            54,
            None,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self._hwnd = int(hwnd)
        user32.ShowWindow(self._hwnd, SW_HIDE)

    def _window_proc(self, hwnd: int, msg: int, w_param: int, l_param: int) -> int:
        try:
            if msg == WM_PAINT:
                self._paint(hwnd)
                return 0
            if msg == WM_TIMER and w_param == HINT_TIMER_ID:
                user32.KillTimer(hwnd, HINT_TIMER_ID)
                user32.ShowWindow(hwnd, SW_HIDE)
                return 0
        except Exception:
            LOGGER.exception("Hint window procedure failed")
        return user32.DefWindowProcW(hwnd, msg, w_param, l_param)

    def _paint(self, hwnd: int) -> None:
        paint = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(paint))
        try:
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            bg = _status_color(UiStatus(self._language, self._enabled))
            bg_brush = gdi32.CreateSolidBrush(bg)
            try:
                user32.FillRect(hdc, ctypes.byref(rect), bg_brush)
            finally:
                gdi32.DeleteObject(bg_brush)

            gdi32.SetBkMode(hdc, TRANSPARENT)
            gdi32.SetTextColor(hdc, _rgb(255, 255, 255))

            label_rect = wintypes.RECT(12, 8, 62, 46)
            label_font = _create_font(-21, FW_BOLD)
            old_font = gdi32.SelectObject(hdc, label_font)
            try:
                user32.DrawTextW(
                    hdc,
                    _language_label(self._language) if self._enabled else "ВЫКЛ",
                    -1,
                    ctypes.byref(label_rect),
                    DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX,
                )
            finally:
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(label_font)

            detail_rect = wintypes.RECT(68, 8, rect.right - 12, 46)
            detail_font = _create_font(-16, FW_SEMIBOLD)
            old_font = gdi32.SelectObject(hdc, detail_font)
            try:
                user32.DrawTextW(
                    hdc,
                    self._text,
                    -1,
                    ctypes.byref(detail_rect),
                    DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX | DT_END_ELLIPSIS,
                )
            finally:
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(detail_font)
        finally:
            user32.EndPaint(hwnd, ctypes.byref(paint))


class DebugLogOverlay:
    def __init__(self) -> None:
        self._class_name = "KeySwitcherDebugLogWindow"
        self._hwnd: int = 0
        self._wndproc = WNDPROC(self._window_proc)
        self._visible = False
        self._entries: list[DebugLogEntry] = []
        self._max_entries = 64
        self._opacity = 210
        self._width = 520
        self._height = 228
        self._x: int | None = None
        self._y: int | None = None
        self._create_window()

    def visible(self) -> bool:
        return self._visible

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        if not self._hwnd:
            return
        if visible:
            x, y = self._current_position()
            user32.SetLayeredWindowAttributes(self._hwnd, 0, self._opacity, LWA_ALPHA)
            user32.SetWindowPos(
                self._hwnd,
                HWND_TOPMOST,
                x,
                y,
                self._width,
                self._height,
                SWP_SHOWWINDOW,
            )
            user32.ShowWindow(self._hwnd, 1)
            user32.InvalidateRect(self._hwnd, None, True)
            user32.UpdateWindow(self._hwnd)
        else:
            self._sync_geometry()
            user32.ShowWindow(self._hwnd, SW_HIDE)

    def append(self, line: str) -> None:
        if not line:
            return
        self._entries.append(_debug_log_style(line[-220:]))
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        if self._visible and self._hwnd:
            user32.InvalidateRect(self._hwnd, None, True)
            user32.UpdateWindow(self._hwnd)

    def close(self) -> None:
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = 0

    def _create_window(self) -> None:
        hinstance = kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSEXW()
        window_class.cbSize = ctypes.sizeof(WNDCLASSEXW)
        window_class.lpfnWndProc = self._wndproc
        window_class.hInstance = hinstance
        window_class.lpszClassName = self._class_name
        atom = user32.RegisterClassExW(ctypes.byref(window_class))
        if not atom and ctypes.get_last_error() != 1410:
            raise ctypes.WinError(ctypes.get_last_error())
        hwnd = user32.CreateWindowExW(
            WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TOOLWINDOW,
            self._class_name,
            "Журнал отладки KeySwitcher",
            WS_POPUP,
            0,
            0,
            self._width,
            self._height,
            None,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self._hwnd = int(hwnd)
        user32.ShowWindow(self._hwnd, SW_HIDE)

    def _window_proc(self, hwnd: int, msg: int, w_param: int, l_param: int) -> int:
        try:
            if msg == WM_NCHITTEST:
                return self._hit_test(hwnd, l_param)
            if msg == WM_PAINT:
                self._paint(hwnd)
                return 0
            if msg in {WM_MOVE, WM_SIZE, WM_EXITSIZEMOVE}:
                self._sync_geometry()
                if self._visible and msg != WM_MOVE:
                    user32.InvalidateRect(hwnd, None, True)
                return 0
        except Exception:
            LOGGER.exception("Debug overlay window procedure failed")
        return user32.DefWindowProcW(hwnd, msg, w_param, l_param)

    def _current_position(self) -> tuple[int, int]:
        if self._x is None or self._y is None:
            self._x, self._y = _overlay_position(self._width, self._height)
        self._x, self._y = _clamp_overlay_position(self._x, self._y, self._width, self._height)
        return self._x, self._y

    def _sync_geometry(self) -> None:
        rect = wintypes.RECT()
        if not self._hwnd or not user32.GetWindowRect(self._hwnd, ctypes.byref(rect)):
            return
        self._x = int(rect.left)
        self._y = int(rect.top)
        self._width = max(320, int(rect.right - rect.left))
        self._height = max(140, int(rect.bottom - rect.top))
        self._x, self._y = _clamp_overlay_position(self._x, self._y, self._width, self._height)

    def _hit_test(self, hwnd: int, l_param: int) -> int:
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return HTCLIENT
        x = _signed_low_word(l_param)
        y = _signed_high_word(l_param)
        border = 8
        title_height = 34

        left = x < rect.left + border
        right = x >= rect.right - border
        top = y < rect.top + border
        bottom = y >= rect.bottom - border

        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM
        if y < rect.top + title_height:
            return HTCAPTION
        return HTCLIENT

    def _paint(self, hwnd: int) -> None:
        paint = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(paint))
        try:
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            bg_brush = gdi32.CreateSolidBrush(_rgb(22, 24, 28))
            try:
                user32.FillRect(hdc, ctypes.byref(rect), bg_brush)
            finally:
                gdi32.DeleteObject(bg_brush)

            border_brush = gdi32.CreateSolidBrush(_rgb(54, 58, 66))
            try:
                user32.FillRect(hdc, ctypes.byref(wintypes.RECT(0, 0, rect.right, 1)), border_brush)
                user32.FillRect(hdc, ctypes.byref(wintypes.RECT(0, rect.bottom - 1, rect.right, rect.bottom)), border_brush)
                user32.FillRect(hdc, ctypes.byref(wintypes.RECT(0, 0, 1, rect.bottom)), border_brush)
                user32.FillRect(hdc, ctypes.byref(wintypes.RECT(rect.right - 1, 0, rect.right, rect.bottom)), border_brush)
            finally:
                gdi32.DeleteObject(border_brush)

            gdi32.SetBkMode(hdc, TRANSPARENT)
            gdi32.SetTextColor(hdc, _rgb(238, 241, 245))

            title_rect = wintypes.RECT(14, 10, rect.right - 14, 34)
            title_font = _create_font(-17, FW_BOLD)
            old_font = gdi32.SelectObject(hdc, title_font)
            try:
                user32.DrawTextW(
                    hdc,
                    "Журнал отладки KeySwitcher",
                    -1,
                    ctypes.byref(title_rect),
                    DT_LEFT | DT_NOPREFIX | DT_SINGLELINE,
                )
            finally:
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(title_font)

            meta_rect = wintypes.RECT(14, 30, rect.right - 14, 46)
            meta_font = _create_font(-13, FW_SEMIBOLD)
            old_font = gdi32.SelectObject(hdc, meta_font)
            gdi32.SetTextColor(hdc, _rgb(147, 154, 165))
            try:
                user32.DrawTextW(
                    hdc,
                    "Перетаскивайте заголовок для перемещения, края и углы для изменения размера.",
                    -1,
                    ctypes.byref(meta_rect),
                    DT_LEFT | DT_NOPREFIX | DT_SINGLELINE | DT_END_ELLIPSIS,
                )
            finally:
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(meta_font)

            line_font = _create_font(-15, FW_SEMIBOLD)
            old_font = gdi32.SelectObject(hdc, line_font)
            try:
                top = 56
                line_height = 20
                badge_width = 42
                capacity = max(3, (rect.bottom - top - 10) // line_height)
                for entry in self._entries[-capacity:]:
                    badge_rect = wintypes.RECT(14, top, 14 + badge_width, top + 16)
                    badge_brush = gdi32.CreateSolidBrush(entry.badge_bg)
                    try:
                        user32.FillRect(hdc, ctypes.byref(badge_rect), badge_brush)
                    finally:
                        gdi32.DeleteObject(badge_brush)

                    gdi32.SetTextColor(hdc, entry.badge_fg)
                    user32.DrawTextW(
                        hdc,
                        entry.badge,
                        -1,
                        ctypes.byref(badge_rect),
                        DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX,
                    )

                    line_rect = wintypes.RECT(62, top - 1, rect.right - 14, top + 18)
                    gdi32.SetTextColor(hdc, _rgb(238, 241, 245))
                    user32.DrawTextW(
                        hdc,
                        entry.line,
                        -1,
                        ctypes.byref(line_rect),
                        DT_LEFT | DT_NOPREFIX | DT_END_ELLIPSIS | DT_SINGLELINE,
                    )
                    top += line_height
            finally:
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(line_font)
        finally:
            user32.EndPaint(hwnd, ctypes.byref(paint))


def _tooltip(status: UiStatus) -> str:
    mode = "активен" if status.enabled else "на паузе"
    language = _language_label(status.language)
    return f"KeySwitcher: {mode}, раскладка {language}. Левый щелчок переключает паузу."


def _hint_text(text: str) -> str:
    if text in HINT_LABELS:
        return HINT_LABELS[text]
    if text.endswith(" rules"):
        count = text[: -len(" rules")].strip()
        return f"{count} правил"
    return text


def _language_label(language: Language) -> str:
    return "RU" if language == "ru" else "EN"


def _status_color(status: UiStatus) -> int:
    if not status.enabled:
        return _rgb(92, 96, 104)
    if status.language == "ru":
        return _rgb(214, 85, 47)
    return _rgb(32, 126, 184)


def _rgb(red: int, green: int, blue: int) -> int:
    return red | (green << 8) | (blue << 16)


def _create_badge_icon(status: UiStatus) -> int:
    size = 32
    hdc_screen = user32.GetDC(None)
    color_dc = gdi32.CreateCompatibleDC(hdc_screen)
    mask_dc = gdi32.CreateCompatibleDC(hdc_screen)
    color_bitmap = gdi32.CreateCompatibleBitmap(hdc_screen, size, size)
    mask_bitmap = gdi32.CreateBitmap(size, size, 1, 1, None)
    old_color = gdi32.SelectObject(color_dc, color_bitmap)
    old_mask = gdi32.SelectObject(mask_dc, mask_bitmap)
    try:
        rect = wintypes.RECT(0, 0, size, size)
        bg_brush = gdi32.CreateSolidBrush(_status_color(status))
        mask_brush = gdi32.CreateSolidBrush(_rgb(0, 0, 0))
        try:
            user32.FillRect(color_dc, ctypes.byref(rect), bg_brush)
            user32.FillRect(mask_dc, ctypes.byref(rect), mask_brush)
        finally:
            gdi32.DeleteObject(bg_brush)
            gdi32.DeleteObject(mask_brush)

        gdi32.SetBkMode(color_dc, TRANSPARENT)
        gdi32.SetTextColor(color_dc, _rgb(255, 255, 255))
        font = _create_font(-12 if status.enabled else -9, FW_BOLD)
        old_font = gdi32.SelectObject(color_dc, font)
        try:
            label = _language_label(status.language) if status.enabled else "ВЫКЛ"
            user32.DrawTextW(
                color_dc,
                label,
                -1,
                ctypes.byref(rect),
                DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX,
            )
        finally:
            gdi32.SelectObject(color_dc, old_font)
            gdi32.DeleteObject(font)

        icon_info = ICONINFO()
        icon_info.fIcon = True
        icon_info.hbmMask = mask_bitmap
        icon_info.hbmColor = color_bitmap
        icon = user32.CreateIconIndirect(ctypes.byref(icon_info))
        if not icon:
            raise ctypes.WinError(ctypes.get_last_error())
        return int(icon)
    finally:
        gdi32.SelectObject(color_dc, old_color)
        gdi32.SelectObject(mask_dc, old_mask)
        gdi32.DeleteObject(color_bitmap)
        gdi32.DeleteObject(mask_bitmap)
        gdi32.DeleteDC(color_dc)
        gdi32.DeleteDC(mask_dc)
        user32.ReleaseDC(None, hdc_screen)


def _create_font(height: int, weight: int) -> int:
    return int(
        gdi32.CreateFontW(
            height,
            0,
            0,
            0,
            weight,
            0,
            0,
            0,
            DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS,
            CLIP_DEFAULT_PRECIS,
            DEFAULT_QUALITY,
            DEFAULT_PITCH,
            "Segoe UI",
        )
    )


def _hint_position(width: int, height: int) -> tuple[int, int]:
    point = _caret_position()
    if point is None:
        point = wintypes.POINT()
        if not user32.GetCursorPos(ctypes.byref(point)):
            point = wintypes.POINT(80, 80)
        x = point.x + 16
        y = point.y + 16
    else:
        x = point.x
        y = point.y - height - 14

    screen_width = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_height = user32.GetSystemMetrics(SM_CYSCREEN)
    x = max(8, min(x, screen_width - width - 8))
    y = max(8, min(y, screen_height - height - 8))
    return x, y


def _overlay_position(width: int, height: int) -> tuple[int, int]:
    screen_width = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_height = user32.GetSystemMetrics(SM_CYSCREEN)
    return max(8, screen_width - width - 16), max(8, screen_height - height - 56)


def _clamp_overlay_position(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    screen_width = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_height = user32.GetSystemMetrics(SM_CYSCREEN)
    clamped_x = max(0, min(x, screen_width - width))
    clamped_y = max(0, min(y, screen_height - height))
    return clamped_x, clamped_y


def _signed_low_word(value: int) -> int:
    word = value & 0xFFFF
    return word - 0x10000 if word & 0x8000 else word


def _signed_high_word(value: int) -> int:
    word = (value >> 16) & 0xFFFF
    return word - 0x10000 if word & 0x8000 else word


def _debug_log_style(line: str) -> DebugLogEntry:
    lowered = line.casefold()
    if (
        "failed" in lowered
        or "error" in lowered
        or "exception" in lowered
        or "ошиб" in lowered
        or "исключени" in lowered
    ):
        return DebugLogEntry("ERR", line, _rgb(184, 63, 63), _rgb(255, 255, 255))
    if "skipped auto-correct" in lowered or "would " in lowered or "пропущ" in lowered or "было бы" in lowered:
        return DebugLogEntry("SKIP", line, _rgb(191, 142, 45), _rgb(31, 24, 8))
    if (
        "correcting " in lowered
        or "applying learned correction" in lowered
        or " switched " in lowered
        or "исправлен" in lowered
        or "применя" in lowered
        or "переключ" in lowered
    ):
        return DebugLogEntry("OK", line, _rgb(53, 148, 86), _rgb(255, 255, 255))
    return DebugLogEntry("INFO", line, _rgb(58, 108, 178), _rgb(255, 255, 255))


def _caret_position() -> wintypes.POINT | None:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    thread_id = user32.GetWindowThreadProcessId(hwnd, None)
    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(GUITHREADINFO)
    if not user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
        return None
    if not info.hwndCaret:
        return None
    point = wintypes.POINT(info.rcCaret.left, info.rcCaret.top)
    if not user32.ClientToScreen(info.hwndCaret, ctypes.byref(point)):
        return None
    return point
