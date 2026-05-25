# Corrector Ollama

Corrector Ollama est un petit correcteur de texte automatique pour Windows, base sur une IA locale via Ollama.
Il surveille la frappe, attend une courte pause, puis propose une correction dans une bulle (Accepter / Ignorer).

## Fonctionnalites

- Correction automatique apres une pause de frappe.
- IA 100% locale via Ollama (aucun appel cloud).
- Protection des champs mot de passe (le buffer est ignore/efface).
- Interface legere en systray.

## Prerequis

- Windows
- Python 3.10+ recommande
- Ollama installe
- Un modele Ollama disponible (ex: `qwen2.5:1.5b`)

## Installation

### Option rapide (script)

```bat
install.bat
```

Ce script:
- installe les dependances Python
- cree un raccourci de demarrage automatique Windows

### Option manuelle

```bat
pip install -r requirements.txt
```

## Lancement

### Avec script

```bat
start.bat
```

`start.bat` tente de se relancer en administrateur (utile pour la capture globale du clavier).

### Manuel

```bat
python main.py
```

## Configuration

Le fichier `config.json` contient:

- `model`: modele Ollama utilise
- `ollama_url`: URL du serveur Ollama (par defaut `http://localhost:11434`)
- `pause_seconds`: delai d'inactivite avant correction
- `min_chars`: nombre minimum de caracteres avant declenchement

Exemple:

```json
{
  "model": "qwen2.5:1.5b",
  "ollama_url": "http://localhost:11434",
  "pause_seconds": 1.5,
  "min_chars": 4
}
```

## Utilisation

1. Lance l'application.
2. Tape du texte dans une zone editable.
3. Fais une pause (selon `pause_seconds`).
4. Une bulle s'affiche avec la proposition de correction.
5. Clique `Accepter` ou `Ignorer` (Entree / Echap aussi).

## Confidentialite

- Les corrections passent par ton Ollama local.
- Aucune donnee n'est envoyee sur Internet par l'application.

## Depannage

- Message `Ollama non disponible`:
  - lance `ollama serve`
  - verifie `ollama_url` dans `config.json`
- Rien ne se passe pendant la frappe:
  - lance en administrateur (`start.bat`)
  - verifie que `min_chars` n'est pas trop eleve
  - teste avec `debug.py` / `debug2.py`
- Modele absent:
  - telecharge-le via Ollama (ex: `ollama pull qwen2.5:1.5b`)

## Structure rapide

- `main.py`: application principale
- `config.json`: configuration
- `requirements.txt`: dependances Python
- `install.bat`: installation + demarrage auto
- `start.bat`: lancement
- `start_hidden.vbs`: lancement silencieux (genere/utilise par les scripts)

