#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publie le contenu d'un dossier local en remplaçant le contenu d'un dépôt GitHub.

Sécurité :
- clone d'abord le dépôt distant dans un dossier temporaire ;
- crée une archive ZIP du dépôt distant avant de le remplacer ;
- demande de saisir REMPLACER avant toute modification ;
- ne touche jamais au dossier source local ;
- conserve l'historique Git du dépôt distant.

Prérequis : Git pour Windows installé et authentification GitHub configurée.
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
from typing import Iterable

DEFAULT_SOURCE = r"C:\Users\hp\Documents\EasyMedicalink\Site web2"
DEFAULT_REPO = "https://github.com/Sastouka/EasyMedicaLinkLocale.git"
DEFAULT_MESSAGE = "Mise a jour du site EasyMedicaLink"

# Fichiers/dossiers techniques qui ne doivent pas être publiés.
IGNORED_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env", "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
}
IGNORED_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
MAX_FILE_BYTES = 100_000_000  # garde-fou : limite usuelle de 100 MB par fichier sur GitHub.


class PublishError(RuntimeError):
    pass


def run_git(args: list[str], cwd: Path | None = None, *, capture: bool = False) -> str:
    cmd = ["git", *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError as exc:
        raise PublishError(
            "Git est introuvable. Installez Git for Windows, puis relancez ce script."
        ) from exc

    if result.returncode != 0:
        details = ""
        if capture:
            details = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        raise PublishError(f"Échec de la commande : {' '.join(cmd)}\n{details}")
    return (result.stdout or "").strip() if capture else ""


def is_ignored(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in IGNORED_DIRS for part in rel.parts):
        return True
    if path.name in IGNORED_FILES or path.suffix.lower() in IGNORED_SUFFIXES:
        return True
    return False


def enumerate_source_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, filenames in os.walk(source):
        current_path = Path(current)
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for filename in filenames:
            candidate = current_path / filename
            if not is_ignored(candidate, source):
                if candidate.is_symlink():
                    print(f"[AVERTISSEMENT] Lien symbolique ignoré : {candidate}")
                    continue
                files.append(candidate)
    return files


def make_remote_backup(repo_dir: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for current, dirs, filenames in os.walk(repo_dir):
            current_path = Path(current)
            dirs[:] = [d for d in dirs if d != ".git"]
            for filename in filenames:
                file_path = current_path / filename
                if ".git" in file_path.relative_to(repo_dir).parts:
                    continue
                archive.write(file_path, file_path.relative_to(repo_dir).as_posix())
    return destination


def clear_clone_except_git(repo_dir: Path) -> None:
    for child in repo_dir.iterdir():
        if child.name.lower() == ".git":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)


def copy_source(source: Path, repo_dir: Path, files: Iterable[Path]) -> None:
    for source_file in files:
        relative = source_file.relative_to(source)
        target = repo_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target)


def ensure_git_identity(repo_dir: Path) -> None:
    name = run_git(["config", "--get", "user.name"], repo_dir, capture=True) if subprocess.run(
        ["git", "config", "--get", "user.name"], cwd=str(repo_dir), stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0 else ""
    email = run_git(["config", "--get", "user.email"], repo_dir, capture=True) if subprocess.run(
        ["git", "config", "--get", "user.email"], cwd=str(repo_dir), stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0 else ""

    if not name:
        name = input("Nom de l'auteur du commit Git : ").strip()
    if not email:
        email = input("E-mail associé à GitHub : ").strip()
    if not name or not email or "@" not in email:
        raise PublishError("Nom ou adresse e-mail Git invalide. Aucun push n'a été effectué.")
    run_git(["config", "user.name", name], repo_dir)
    run_git(["config", "user.email", email], repo_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remplace le contenu du dépôt GitHub par celui d'un dossier local."
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Dossier local à publier.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="URL HTTPS du dépôt GitHub.")
    parser.add_argument("--message", default=DEFAULT_MESSAGE, help="Message du commit Git.")
    parser.add_argument(
        "--backup-dir", default=None,
        help="Dossier où enregistrer l'archive de sauvegarde (par défaut, à côté du dossier source).",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Confirme automatiquement le remplacement (à utiliser uniquement en connaissance de cause).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        raise PublishError(f"Dossier source introuvable : {source}")
    if not (source / "index.html").is_file():
        raise PublishError(
            f"index.html introuvable à la racine de : {source}\n"
            "Le script s'arrête pour éviter de publier le mauvais dossier."
        )

    source_files = enumerate_source_files(source)
    if not source_files:
        raise PublishError("Aucun fichier à publier n'a été trouvé.")

    too_large = [(p, p.stat().st_size) for p in source_files if p.stat().st_size >= MAX_FILE_BYTES]
    if too_large:
        details = "\n".join(f"- {p} ({size / (1024 * 1024):.1f} Mo)" for p, size in too_large)
        raise PublishError(
            "Un ou plusieurs fichiers atteignent la limite de taille prévue par ce script :\n"
            f"{details}\nRetirez-les ou utilisez Git LFS avant de publier."
        )

    print("\n=== PUBLICATION EASYMEDICALINK SUR GITHUB ===")
    print(f"Dossier source : {source}")
    print(f"Dépôt cible    : {args.repo}")
    print(f"Fichiers       : {len(source_files)}")
    print("Action         : remplacer les fichiers du dépôt distant par ceux du dossier source.")
    print("Conservation   : l'historique Git du dépôt sera conservé ; le dossier source ne sera pas modifié.")

    temp_root = Path(tempfile.mkdtemp(prefix="easymedicalink_publish_"))
    repo_dir = temp_root / "repository"
    keep_temp_on_error = True
    try:
        print("\n[1/6] Connexion et récupération du dépôt distant...")
        run_git(["clone", args.repo, str(repo_dir)])
        branch = run_git(["branch", "--show-current"], repo_dir, capture=True)
        if not branch:
            raise PublishError("Impossible de déterminer la branche par défaut du dépôt après le clonage.")

        backup_root = Path(args.backup_dir).expanduser().resolve() if args.backup_dir else source.parent
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_root / f"Sauvegarde_EasyMedicaLink_GitHub_{stamp}.zip"

        print(f"Branche détectée : {branch}")
        print(f"Sauvegarde prévue : {backup_path}")
        if args.yes:
            confirmed = True
        else:
            answer = input(
                "\nATTENTION : le contenu actuel du dépôt sera remplacé.\n"
                "Tapez exactement REMPLACER pour continuer : "
            ).strip()
            confirmed = answer == "REMPLACER"
        if not confirmed:
            print("Opération annulée. Le dépôt distant n'a pas été modifié.")
            keep_temp_on_error = False
            return 0

        print("\n[2/6] Sauvegarde du contenu actuel du dépôt...")
        make_remote_backup(repo_dir, backup_path)

        print("[3/6] Nettoyage de la copie temporaire (historique Git conservé)...")
        clear_clone_except_git(repo_dir)

        print("[4/6] Copie de la nouvelle version...")
        copy_source(source, repo_dir, source_files)
        if not (repo_dir / "index.html").is_file():
            raise PublishError("Le fichier index.html n'a pas été copié correctement. Push annulé.")

        print("[5/6] Préparation du commit...")
        run_git(["add", "-A"], repo_dir)
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=str(repo_dir),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if diff.returncode == 0:
            print("Le dépôt contient déjà exactement cette version. Aucun commit n'est nécessaire.")
            print(f"Sauvegarde créée : {backup_path}")
            keep_temp_on_error = False
            return 0
        if diff.returncode not in (0, 1):
            raise PublishError("Impossible de vérifier les changements Git. Push annulé.")

        ensure_git_identity(repo_dir)
        run_git(["commit", "-m", args.message], repo_dir)

        print("[6/6] Envoi vers GitHub...")
        run_git(["push", "origin", branch], repo_dir)

        print("\n[SUCCÈS] Le dépôt GitHub a été mis à jour.")
        print(f"Dépôt : {args.repo}")
        print(f"Branche : {branch}")
        print(f"Sauvegarde du dépôt précédent : {backup_path}")
        print("Le dossier local source n'a pas été modifié.")
        keep_temp_on_error = False
        return 0

    except PublishError:
        raise
    except KeyboardInterrupt:
        print("\nOpération interrompue par l'utilisateur.")
        return 130
    finally:
        # Conserver la copie temporaire en cas d'échec pour faciliter le diagnostic.
        if not keep_temp_on_error and temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PublishError as exc:
        print(f"\n[ERREUR] {exc}", file=sys.stderr)
        print("Le dépôt distant n'a pas été poussé par ce script.", file=sys.stderr)
        sys.exit(1)
