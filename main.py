"""
Corrector Ollama v4
- Correction automatique apres pause de frappe
- Correction de code selectione via Ctrl+Shift+K
- Protection champs mot de passe (buffer efface automatiquement)
- 100% local via Ollama, aucune donnee envoyee sur internet
"""

import tkinter as tk
import threading
import queue
import time
import os
import json
import ctypes

import keyboard
import requests
import win32api
import win32clipboard
import win32con
import win32gui
from PIL import Image, ImageDraw
import pystray

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "model":         "qwen2.5:1.5b",
    "ollama_url":    "http://localhost:11434",
    "pause_seconds": 1.5,
    "min_chars":     4
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

cfg = load_config()

# ── Securite : detection champ mot de passe ───────────────────────────────────
# Couvre les champs Win32 natifs ET les navigateurs web (Chrome, Firefox, Edge).

_pwd_cache      = False
_pwd_cache_time = 0.0

# Titres de fenetres / classes qui indiquent un navigateur
_BROWSER_CLASSES = {"Chrome_WidgetWin_1", "MozillaWindowClass",
                    "ApplicationFrameWindow", "EdgeHTML"}

def _is_win32_password_field() -> bool:
    """EM_GETPASSWORDCHAR : detecte les vrais champs Win32 type=password."""
    try:
        hwnd   = win32gui.GetForegroundWindow()
        fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        ctypes.windll.user32.AttachThreadInput(my_tid, fg_tid, True)
        focused = ctypes.windll.user32.GetFocus()
        ctypes.windll.user32.AttachThreadInput(my_tid, fg_tid, False)
        if focused:
            return ctypes.windll.user32.SendMessageW(focused, 0x00D2, 0, 0) != 0
    except Exception:
        pass
    return False

def _is_browser_foreground() -> bool:
    """Retourne True si le focus est dans un navigateur web."""
    try:
        hwnd  = win32gui.GetForegroundWindow()
        cls   = win32gui.GetClassName(hwnd)
        return cls in _BROWSER_CLASSES
    except Exception:
        return False

def is_password_field() -> bool:
    """
    Detecte si l'utilisateur tape dans un champ mot de passe.
    - Champs Win32 natifs  : EM_GETPASSWORDCHAR
    - Navigateurs web      : on efface le buffer en permanence quand le
                             titre de fenetre contient des mots-cles suspects.
    Cache de 400ms pour ne pas surcharger.
    """
    global _pwd_cache, _pwd_cache_time
    now = time.time()
    if now - _pwd_cache_time < 0.4:
        return _pwd_cache
    _pwd_cache_time = now

    # 1. Champ Win32 natif
    if _is_win32_password_field():
        _pwd_cache = True
        return True

    # 2. Navigateur : impossible de detecter type=password depuis l'exterieur.
    #    On protege en cherchant des mots-cles dans le titre de la fenetre.
    try:
        hwnd  = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd).lower()
        PWD_KEYWORDS = ("sign in", "log in", "login", "connexion",
                        "password", "mot de passe", "se connecter",
                        "authentification", "unlock")
        if any(k in title for k in PWD_KEYWORDS):
            _pwd_cache = True
            return True
    except Exception:
        pass

    _pwd_cache = False
    return False

# ── Ollama ────────────────────────────────────────────────────────────────────

PROMPT_TEXT = (
    "Corrige les fautes d'orthographe et grammaire. "
    "Reponds uniquement avec le texte corrige, sans explication.\n"
    "Texte: {text}"
)

def ollama_call(text, prompt_template):
    try:
        r = requests.post(
            f"{cfg['ollama_url']}/api/generate",
            json={
                "model":   cfg["model"],
                "prompt":  prompt_template.format(text=text),
                "stream":  False,
                "options": {"temperature": 0.1}
            },
            timeout=60
        )
        r.raise_for_status()
        return r.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        return "__CONN_ERROR__"
    except Exception:
        return "__ERROR__"

# ── Clipboard ─────────────────────────────────────────────────────────────────

_cb_lock = threading.Lock()

def _cb_get():
    with _cb_lock:
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return data or ""
        except Exception:
            try: win32clipboard.CloseClipboard()
            except Exception: pass
            return ""

def _cb_set(text):
    with _cb_lock:
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
        except Exception:
            try: win32clipboard.CloseClipboard()
            except Exception: pass

# ── Buffer de frappe ──────────────────────────────────────────────────────────

_synthetic = threading.Event()

RESET_KEYS = {
    "left", "right", "up", "down",
    "home", "end", "page up", "page down",
    "enter", "return", "escape", "tab", "insert",
}

IGNORE_KEYS = {
    "ctrl", "shift", "alt", "windows", "cmd",
    "caps lock", "num lock", "scroll lock",
    "print screen", "pause", "menu",
    "f1","f2","f3","f4","f5","f6",
    "f7","f8","f9","f10","f11","f12",
}

class TypingBuffer:
    def __init__(self):
        self._buf  = ""
        self._lock = threading.Lock()

    def push(self, event):
        if _synthetic.is_set():
            return

        # Securite : ne rien capturer dans un champ mot de passe
        if is_password_field():
            self.clear()
            return

        if keyboard.is_pressed("ctrl") or keyboard.is_pressed("alt"):
            self.clear()
            return

        name = event.name
        if name in IGNORE_KEYS:
            return
        if name in RESET_KEYS:
            self.clear()
            return
        if name == "backspace":
            with self._lock:
                self._buf = self._buf[:-1]
            return

        ch = self._char(name)
        if ch:
            with self._lock:
                self._buf += ch
                if len(self._buf) > 600:
                    self._buf = self._buf[-600:]

    def _char(self, name):
        if name == "space":
            return " "
        if len(name) == 1:
            shift = bool(win32api.GetKeyState(win32con.VK_SHIFT)  & 0x8000)
            caps  = bool(win32api.GetKeyState(win32con.VK_CAPITAL) & 0x0001)
            upper = (shift and not caps) or (not shift and caps)
            return name.upper() if upper else name
        return None

    def snapshot_and_clear(self):
        with self._lock:
            t, self._buf = self._buf, ""
            return t

    def clear(self):
        with self._lock:
            self._buf = ""

    @property
    def size(self):
        with self._lock:
            return len(self._buf)

_buf = TypingBuffer()

# ── Surveillance des frappes ──────────────────────────────────────────────────

_last_key_time = 0.0
_time_lock     = threading.Lock()

def on_key_press(event):
    global _last_key_time
    if _synthetic.is_set():
        return

    name = event.name
    if name in IGNORE_KEYS:
        return
    if keyboard.is_pressed("ctrl") or keyboard.is_pressed("alt"):
        return

    with _time_lock:
        _last_key_time = time.time()

    _buf.push(event)
    _evt_queue.put(("close",))

# ── Correction automatique (texte) ────────────────────────────────────────────

_correction_active = threading.Event()

def monitor_loop():
    while True:
        time.sleep(0.2)

        if _correction_active.is_set():
            continue

        with _time_lock:
            idle = time.time() - _last_key_time if _last_key_time else 9999.0

        if idle >= cfg["pause_seconds"] and _buf.size >= cfg["min_chars"]:
            _correction_active.set()
            text = _buf.snapshot_and_clear()

            try:
                tgt_hwnd = win32gui.GetForegroundWindow()
            except Exception:
                tgt_hwnd = None
            try:
                cx, cy = win32api.GetCursorPos()
            except Exception:
                cx, cy = 400, 400

            threading.Thread(
                target=_bg_text_correction,
                args=(text, cx, cy, tgt_hwnd),
                daemon=True
            ).start()

def _bg_text_correction(text, cx, cy, tgt_hwnd):
    if not text or not text.strip() or len(text.strip()) < 3:
        _correction_active.clear()
        return
    corrected = ollama_call(text, PROMPT_TEXT)
    _evt_queue.put(("show_result", text, corrected, cx, cy, tgt_hwnd))

def _force_foreground(hwnd):
    """
    SetForegroundWindow fiable via AttachThreadInput.
    Contourne les restrictions Windows sur le changement de fenetre active.
    """
    if not hwnd:
        return
    try:
        cur     = win32gui.GetForegroundWindow()
        cur_tid = ctypes.windll.user32.GetWindowThreadProcessId(cur, None)
        tgt_tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        my_tid  = ctypes.windll.kernel32.GetCurrentThreadId()

        ctypes.windll.user32.AttachThreadInput(my_tid, cur_tid, True)
        ctypes.windll.user32.AttachThreadInput(my_tid, tgt_tid, True)
        win32gui.SetForegroundWindow(hwnd)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.AttachThreadInput(my_tid, cur_tid, False)
        ctypes.windll.user32.AttachThreadInput(my_tid, tgt_tid, False)
    except Exception:
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

def apply_text_correction(original, corrected, tgt_hwnd):
    """
    Selectionne len(original) caracteres en arriere (Shift+Left x N)
    puis colle le texte corrige. Plus fiable que les backspaces.
    """
    _force_foreground(tgt_hwnd)
    time.sleep(0.15)

    saved = _cb_get()
    _cb_set(corrected)
    _synthetic.set()
    try:
        # Selectionner exactement N caracteres en arriere
        keyboard.press("shift")
        for _ in range(len(original)):
            keyboard.press_and_release("left")
        keyboard.release("shift")
        time.sleep(0.04)
        # Coller → remplace la selection
        keyboard.send("ctrl+v")
        time.sleep(0.05)
    finally:
        _synthetic.clear()
    _cb_set(saved)

# ── Event queue ───────────────────────────────────────────────────────────────

_evt_queue = queue.Queue()

def process_queue():
    try:
        while True:
            evt = _evt_queue.get_nowait()
            kind = evt[0]
            if kind == "close":
                _close_bubble()
            elif kind == "show_result":
                _, original, corrected, cx, cy, tgt_hwnd = evt
                _show_result(original, corrected, cx, cy, tgt_hwnd)
                _correction_active.clear()
    except queue.Empty:
        pass
    root.after(60, process_queue)

# ── UI Bubble ─────────────────────────────────────────────────────────────────

root       = None
bubble_win = None

C_BG     = "#16213e"
C_BG2    = "#0f0f23"
C_BORDER = "#7c3aed"
C_ACCENT = "#a78bfa"
C_TEXT   = "#e2e8f0"
C_MUTED  = "#64748b"
C_GREEN  = "#10b981"
C_RED    = "#ef4444"

def _close_bubble():
    global bubble_win
    if bubble_win:
        try:
            bubble_win.destroy()
        except Exception:
            pass
        bubble_win = None

def _place(win, cx, cy):
    win.update_idletasks()
    w  = win.winfo_reqwidth()
    h  = win.winfo_reqheight()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x  = max(10, min(cx, sw - w - 10))
    y  = cy + 22
    if y + h > sh - 48:
        y = cy - h - 14
    win.geometry(f"+{x}+{y}")

def _show_result(original, corrected, cx, cy, tgt_hwnd):
    global bubble_win
    _close_bubble()

    is_error  = corrected.startswith("__")
    no_change = (not is_error) and original.strip() == corrected.strip()

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=C_BORDER)

    f = tk.Frame(win, bg=C_BG, padx=14, pady=10)
    f.pack(padx=2, pady=2)

    # En-tete
    hdr = tk.Frame(f, bg=C_BG)
    hdr.pack(fill="x", pady=(0, 6))
    tk.Label(hdr, text="Corrector Ollama", bg=C_BG, fg=C_ACCENT,
             font=("Segoe UI", 8, "bold")).pack(side="left")
    x_lbl = tk.Label(hdr, text="x", bg=C_BG, fg=C_MUTED,
                     font=("Segoe UI", 8), cursor="hand2")
    x_lbl.pack(side="right")
    x_lbl.bind("<Button-1>", lambda e: _close_bubble())

    if is_error:
        msg = "Ollama non disponible - lancez : ollama serve" \
              if corrected == "__CONN_ERROR__" else "Erreur de correction"
        tk.Label(f, text=msg, bg=C_BG, fg=C_RED,
                 font=("Segoe UI", 9)).pack(pady=4)
        root.after(4000, _close_bubble)

    elif no_change:
        tk.Label(f, text="Aucune faute detectee !", bg=C_BG, fg=C_GREEN,
                 font=("Segoe UI", 9, "bold")).pack(pady=4)
        root.after(1800, _close_bubble)

    else:
        preview = corrected[:300] + ("..." if len(corrected) > 300 else "")
        n_lines = preview.count("\n") + 1

        t = tk.Text(f, bg=C_BG2, fg=C_TEXT, font=("Segoe UI", 9),
                    relief="flat", wrap="word", width=52,
                    height=min(n_lines + 1, 5),
                    padx=6, pady=4, bd=0,
                    highlightthickness=1, highlightbackground="#2a2a4a",
                    state="normal")
        t.insert("1.0", preview)
        t.configure(state="disabled")
        t.pack(fill="x", pady=(0, 8))

        sep = tk.Frame(f, bg="#2a2a4a", height=1)
        sep.pack(fill="x", pady=(0, 6))

        btns = tk.Frame(f, bg=C_BG)
        btns.pack(fill="x")

        def accept():
            _close_bubble()
            root.after(80, lambda: apply_text_correction(original, corrected, tgt_hwnd))

        tk.Button(btns, text="Accepter", bg=C_GREEN, fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat",
                  padx=14, pady=4, cursor="hand2", bd=0,
                  activebackground="#059669",
                  command=accept).pack(side="left", padx=(0, 6))

        tk.Button(btns, text="Ignorer", bg="#1e293b", fg=C_MUTED,
                  font=("Segoe UI", 9), relief="flat",
                  padx=10, pady=4, cursor="hand2", bd=0,
                  activebackground="#374151",
                  command=_close_bubble).pack(side="left")

        tk.Label(f, text="Entree=accepter  Echap=ignorer",
                 bg=C_BG, fg=C_MUTED, font=("Segoe UI", 7)).pack(
                     anchor="w", pady=(6, 0))

        win.bind("<Return>", lambda e: accept())
        win.bind("<Escape>", lambda e: _close_bubble())
        win.after(150, win.focus_force)
        root.after(10000, _close_bubble)

    _place(win, cx, cy)
    bubble_win = win

# ── Icone systray ─────────────────────────────────────────────────────────────

def _make_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([2, 2, 62, 62], fill=(124, 58, 237))
    d.line([(16, 34), (27, 46), (50, 20)], fill=(255, 255, 255), width=6)
    return img

def run_tray():
    def quit_app(icon, _):
        keyboard.unhook_all()
        icon.stop()
        if root:
            root.after(0, root.quit)

    icon = pystray.Icon(
        "corrector_ollama",
        _make_icon(),
        "Corrector Ollama",
        menu=pystray.Menu(
            pystray.MenuItem(f"Modele : {cfg['model']}",           None, enabled=False),
            pystray.MenuItem(f"Delai  : {cfg['pause_seconds']}s", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", quit_app),
        )
    )
    icon.run()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global root

    root = tk.Tk()
    root.withdraw()

    keyboard.on_press(on_key_press)


    root.after(100, process_queue)
    threading.Thread(target=monitor_loop, daemon=True).start()
    threading.Thread(target=run_tray,     daemon=True).start()

    print("Corrector Ollama demarre.")
    print(f"  Modele      : {cfg['model']}")
    print(f"  Correction auto apres {cfg['pause_seconds']}s de pause")
    print(f"  Securite : champs mot de passe ignores automatiquement")

    root.mainloop()

if __name__ == "__main__":
    main()
