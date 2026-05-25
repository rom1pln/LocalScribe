import sys
import time

print("=== DEBUG Corrector Ollama ===\n")

# 1. Test keyboard
print("[1] Test keyboard...")
try:
    import keyboard
    detected = []
    keyboard.on_press(lambda e: detected.append(e.name))
    print("    OK - Tape quelque chose dans les 5 secondes...")
    time.sleep(5)
    if detected:
        print(f"    DETECTE : {detected[:5]}")
    else:
        print("    RIEN detecte - relance en ADMINISTRATEUR (clic droit -> Executer en tant qu'administrateur)")
    keyboard.unhook_all()
except Exception as e:
    print(f"    ERREUR : {e}")

# 2. Test Ollama
print("\n[2] Test Ollama...")
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=3)
    models = [m["name"] for m in r.json().get("models", [])]
    print(f"    OK - Modeles disponibles : {models}")
except Exception as e:
    print(f"    ERREUR : {e}")
    print("    -> Lance 'ollama serve' dans un terminal")

# 3. Test clipboard
print("\n[3] Test clipboard...")
try:
    import win32clipboard, win32con
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, "test123")
    data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    print(f"    OK - Lu : {data}")
except Exception as e:
    print(f"    ERREUR : {e}")

# 4. Test tkinter
print("\n[4] Test tkinter...")
try:
    import tkinter as tk
    r = tk.Tk()
    r.withdraw()
    r.destroy()
    print("    OK")
except Exception as e:
    print(f"    ERREUR : {e}")

print("\n=== FIN DEBUG ===")
input("\nAppuie sur Entree pour quitter.")
