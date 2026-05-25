import keyboard
import time

print("Test du raccourci clavier")
print("Appuie sur Ctrl+Shift+Espace dans les 10 secondes...")
print()

detected = []

def on_key():
    print(">>> RACCOURCI DETECTE ! Ca marche.")
    detected.append(True)

keyboard.add_hotkey("ctrl+shift+space", on_key)

for i in range(10, 0, -1):
    print(f"\rAttente... {i}s   ", end="", flush=True)
    time.sleep(1)
    if detected:
        break

print()
if not detected:
    print(">>> Rien detecte. Essaie de relancer en administrateur.")
    print("    Clic droit sur ce script -> Executer en tant qu'administrateur")

input("\nAppuie sur Entree pour quitter.")
