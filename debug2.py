"""
Debug : simule exactement la logique de main.py sans UI ni Ollama.
Ouvre Notepad ou un navigateur, tape du texte, attends 2s.
"""
import keyboard
import threading
import time
import win32clipboard, win32con

_last_key_time = 0.0
_chars_typed   = 0
_lock          = threading.Lock()
_synthetic     = threading.Event()

IGNORED = {"ctrl","shift","alt","windows","cmd","caps lock","f1","f2","f3",
           "f4","f5","f6","f7","f8","f9","f10","f11","f12"}
NAV     = {"left","right","up","down","home","end","page up","page down"}

def on_key(event):
    global _last_key_time, _chars_typed
    if _synthetic.is_set():
        return
    name = event.name
    if keyboard.is_pressed("ctrl") or keyboard.is_pressed("alt"):
        return
    if name in IGNORED or name in NAV:
        return
    if name in ("enter","return","escape","tab"):
        with _lock:
            _chars_typed = 0
        return
    with _lock:
        _last_key_time = time.time()
        _chars_typed  += 1
        c = _chars_typed
    print(f"[KEY] '{name}'  chars_typed={c}")

keyboard.on_press(on_key)
print("Ouvre Notepad ou Chrome, tape du texte, attends 2 secondes...")
print("Ctrl+C ici pour quitter.\n")

while True:
    time.sleep(0.3)
    with _lock:
        idle  = time.time() - _last_key_time if _last_key_time else 9999
        chars = _chars_typed

    if idle >= 1.5 and chars >= 4:
        print(f"\n>>> DECLENCHEMENT ! idle={idle:.1f}s  chars={chars}")
        with _lock:
            _chars_typed = 0

        # Recupere la ligne courante
        print(">>> get_current_line()...")
        saved = ""
        try:
            win32clipboard.OpenClipboard()
            try: saved = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except: pass
            win32clipboard.CloseClipboard()
        except: pass

        _synthetic.set()
        keyboard.send("home")
        time.sleep(0.05)
        keyboard.send("shift+end")
        time.sleep(0.05)
        keyboard.send("ctrl+c")
        time.sleep(0.2)
        _synthetic.clear()

        try:
            win32clipboard.OpenClipboard()
            try: text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except: text = ""
            win32clipboard.CloseClipboard()
        except: text = ""

        # Restore clipboard
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            if saved:
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, saved)
            win32clipboard.CloseClipboard()
        except: pass

        print(f">>> Texte recupere : '{text}'")
        if text:
            print(">>> SUCCES - La correction Ollama serait lancee ici.")
        else:
            print(">>> ECHEC - Ligne vide, rien a corriger.")
        print()
