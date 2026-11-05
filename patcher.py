#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publie le contenu d'un dossier local dans un dépôt GitHub existant.
- Conserve l'historique Git distant (clone + commit + push).
- Sauvegarde le contenu actuel du dépôt dans un ZIP avant remplacement.
- N'efface jamais le dépôt distant avant confirmation.
- Exclut les secrets, environnements virtuels et fichiers temporaires courants.

Prérequis : Git pour Windows installé et authentification GitHub configurée.
Exécution :
  py mettre_a_jour_depot.py
  py mettre_a_jour_depot.py --source "C:\\Users\\hp\\Documents\\EasyMedicalink\\Site web2"
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

REPOSITORY_URL = "https://github.com/Sastouka/EasyMedicaLinkLocale.git"
DEFAULT_SOURCE = r"C:\Users\hp\Documents\EasyMedicalink\Site web2"

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", ".idea", ".vscode",
}
EXCLUDED_FILES = {
    ".env", ".env.local", ".env.production", "secrets.json",
    "credentials.json", "id_rsa", "id_ed25519",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".sqlite", ".sqlite3", ".db"}
EXCLUDED_PREFIXES = (".",)
EXCLUDED_NAME_PARTS = (".backup_", ".bak", ".tmp")


def run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(command))
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if check and result.returncode != 0:
        raise RuntimeError(f"Commande échouée (code {result.returncode}) : {' '.join(command)}")
    return result


def included(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    name = path.name.lower()
    if name in EXCLUDED_FILES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if any(part in name for part in EXCLUDED_NAME_PARTS):
        return False
    # Eviter les fichiers système cachés, tout en gardant les .well-known utiles au site.
    if name.startswith(".") and name not in {".nojekyll"} and not name.startswith(".well-known"):
        return False
    return True


def make_backup(repo_dir: Path, backup_dir: Path, branch: str) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = backup_dir / f"EasyMedicaLinkLocale_avant_{stamp}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in repo_dir.rglob("*"):
            if file.is_file() and ".git" not in file.relative_to(repo_dir).parts:
                if included(file, repo_dir):
                    zf.write(file, file.relative_to(repo_dir).as_posix())
        zf.writestr("_BACKUP_INFO.txt", f"Dépôt : {REPOSITORY_URL}\nBranche : {branch}\nDate : {stamp}\n")
    return archive


def copy_source(source: Path, destination: Path) -> int:
    count = 0
    for item in source.rglob("*"):
        if not item.is_file() or not included(item, source):
            continue
        relative = item.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        count += 1
    if count == 0:
        raise RuntimeError("Aucun fichier publiable détecté dans le dossier source.")
    return count


def clean_worktree(repo_dir: Path) -> None:
    for item in repo_dir.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Met à jour EasyMedicaLinkLocale depuis Site web2.")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Dossier local à publier")
    parser.add_argument("--repo", default=REPOSITORY_URL, help="URL HTTPS ou SSH du dépôt Git")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        print(f"[ERREUR] Dossier source introuvable : {source}")
        return 2
    if shutil.which("git") is None:
        print("[ERREUR] Git est introuvable. Installez Git for Windows puis rouvrez PowerShell.")
        return 2

    # Sauvegardes en dehors du dossier publié afin de ne jamais les envoyer sur GitHub.
    backup_dir = source.parent / "Sauvegardes_publication_GitHub"
    print("\n=== PUBLICATION EasyMedicaLinkLocale ===")
    print(f"Source : {source}")
    print(f"Dépôt  : {args.repo}")
    print("Les fichiers de configuration sensibles, bases locales, journaux et caches seront exclus.")
    print("Les dossiers et images du site (dont asset/) seront conservés.")

    with tempfile.TemporaryDirectory(prefix="eml_github_publish_") as temp:
        clone_dir = Path(temp) / "repository"
        run(["git", "clone", args.repo, str(clone_dir)])
        branch_result = run(["git", "branch", "--show-current"], cwd=clone_dir)
        branch = branch_result.stdout.strip()
        if not branch:
            raise RuntimeError("Impossible de déterminer la branche active du dépôt cloné.")
        run(["git", "remote", "-v"], cwd=clone_dir)

        backup = make_backup(clone_dir, backup_dir, branch)
        print(f"\n[SAUVEGARDE] {backup}")

        clean_worktree(clone_dir)
        copied = copy_source(source, clone_dir)
        print(f"\n[FICHIERS] {copied} fichier(s) préparé(s) pour publication.")

        run(["git", "add", "-A"], cwd=clone_dir)
        status = run(["git", "status", "--short"], cwd=clone_dir, check=False)
        if not status.stdout.strip():
            print("[INFO] Le dépôt distant contient déjà exactement cette version. Aucun commit nécessaire.")
            return 0

        print("\nAperçu des changements :")
        run(["git", "diff", "--cached", "--stat"], cwd=clone_dir)

        # Identité Git locale au clone temporaire, sans modifier la configuration globale.
        name = run(["git", "config", "user.name"], cwd=clone_dir, check=False).stdout.strip()
        email = run(["git", "config", "user.email"], cwd=clone_dir, check=False).stdout.strip()
        if not name:
            name = "Sastouka Digital"
            run(["git", "config", "user.name", name], cwd=clone_dir)
        if not email:
            email = "sastoukadigital@gmail.com"
            run(["git", "config", "user.email", email], cwd=clone_dir)

        answer = input("\nPour confirmer le remplacement du contenu du dépôt, tapez PUBLIER : ").strip()
        if answer != "PUBLIER":
            print("[ANNULÉ] Aucune modification n'a été envoyée sur GitHub.")
            print(f"La sauvegarde ZIP reste disponible : {backup}")
            return 0

        message = f"Publier la nouvelle version du site EasyMedicaLink ({datetime.now():%Y-%m-%d %H:%M})"
        run(["git", "commit", "-m", message], cwd=clone_dir)
        run(["git", "push", "origin", branch], cwd=clone_dir)
        print("\n[SUCCÈS] Le dépôt GitHub a été mis à jour.")
        print(f"Branche : {branch}")
        print(f"Sauvegarde : {backup}")
        print(f"URL : https://github.com/Sastouka/EasyMedicaLinkLocale")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTION] Publication annulée.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\n[ERREUR] {exc}")
        print("Le dépôt distant n'a pas été poussé si l'étape git push n'a pas été atteinte.")
        raise SystemExit(1)
