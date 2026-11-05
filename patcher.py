#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nettoie les doublons connus d'EasyMedicaLink puis publie Site web2 sur GitHub.

- Nettoyage conservateur des cartes HD répétées dans une même grille.
- Retrait des images 11.png / 12.png du carrousel générique lorsqu'elles ont
  déjà leur propre rubrique dédiée.
- Ajout du correctif mobile des deux boutons flottants (une seule fois).
- Sauvegarde locale de index.html et archive ZIP du dépôt distant avant remplacement.
- Conserve l'historique Git et ne modifie jamais les autres fichiers du dossier source.
"""
from __future__ import annotations
import argparse, hashlib, os, re, shutil, subprocess, sys, tempfile, zipfile
from datetime import datetime
from pathlib import Path

DEFAULT_SOURCE = r"C:\Users\hp\Documents\EasyMedicalink\Site web2"
DEFAULT_REPO = "https://github.com/Sastouka/EasyMedicaLinkLocale.git"
MAX_FILE_BYTES = 100_000_000
IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORED_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
DIV_TOKEN = re.compile(r"</?div\b[^>]*>", re.I)
ATTR_CLASS = re.compile(r'\bclass\s*=\s*["\']([^"\']*)["\']', re.I)
ATTR_SRC = re.compile(r'\bsrc\s*=\s*["\']([^"\']*)["\']', re.I)
ATTR_CAPTURE = re.compile(r'\bdata-eml-capture\s*=\s*["\']([^"\']*)["\']', re.I)

class TaskError(RuntimeError): pass

def run_git(args: list[str], cwd: Path | None = None, capture: bool = False) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=str(cwd) if cwd else None, text=True,
            encoding="utf-8", errors="replace", stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None)
    except FileNotFoundError as e:
        raise TaskError("Git est introuvable. Installez Git for Windows.") from e
    if p.returncode:
        detail = "\n".join(x for x in (p.stdout, p.stderr) if x).strip() if capture else ""
        raise TaskError(f"Commande Git échouée : git {' '.join(args)}\n{detail}")
    return (p.stdout or "").strip() if capture else ""

def div_blocks(doc: str):
    stack, blocks = [], []
    for m in DIV_TOKEN.finditer(doc):
        token = m.group(0)
        if token.lstrip().startswith("</"):
            if stack:
                start, opening = stack.pop()
                cm = ATTR_CLASS.search(opening)
                classes = set(cm.group(1).split()) if cm else set()
                blocks.append((start, m.end(), opening, classes))
        elif not token.rstrip().endswith("/>"):
            stack.append((m.start(), token))
    return sorted(blocks, key=lambda x: x[0])

def clean_duplicate_feature_cards(doc: str) -> tuple[str, int]:
    seen, removals = set(), []
    for start, end, opening, classes in div_blocks(doc):
        if not {"feature-card", "eml-added-feature-card"}.issubset(classes) or not ATTR_CAPTURE.search(opening):
            continue
        normalized = re.sub(r"\s+", " ", doc[start:end]).strip()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if digest in seen: removals.append((start, end))
        else: seen.add(digest)
    for start, end in reversed(removals): doc = doc[:start] + doc[end:]
    return doc, len(removals)

def clean_hero_doc_repeats(doc: str) -> tuple[str, int]:
    removed = 0
    blocks = div_blocks(doc)
    for basename in ("11.png", "12.png"):
        has_dedicated = False
        for a, b, _, classes in blocks:
            if "img-col" in classes:
                chunk = doc[a:b]
                if re.search(r'<img\b[^>]*\bsrc=["\'](?:asset/)?' + re.escape(basename) + r'["\']', chunk, re.I):
                    has_dedicated = True; break
        if not has_dedicated: continue
        removals = []
        for a, b, _, classes in blocks:
            if "doc-item" not in classes: continue
            chunk = doc[a:b]
            if not re.search(r'<img\b[^>]*\bsrc=["\'](?:asset/)?' + re.escape(basename) + r'["\']', chunk, re.I): continue
            inside = any("doc-scroll-container" in parent_classes and pa <= a < b <= pb
                         for pa, pb, _, parent_classes in blocks)
            if inside: removals.append((a, b))
        for a, b in reversed(removals): doc = doc[:a] + doc[b:]
        removed += len(removals)
        blocks = div_blocks(doc)
    return doc, removed

MOBILE_CSS = r'''
/* EML_MOBILE_DOWNLOAD_BUTTONS_PUBLISH_V1 */
@media (max-width: 768px) {
  #dragDownloads.floating-downloads {
    position: fixed !important;
    right: max(12px, env(safe-area-inset-right, 0px)) !important;
    bottom: max(16px, env(safe-area-inset-bottom, 0px)) !important;
    z-index: 9998 !important; display: flex !important;
    flex-direction: column !important; align-items: flex-end !important; gap: 9px !important;
  }
  #dragDownloads .btn-float {
    display: inline-flex !important; align-items: center !important; justify-content: center !important;
    gap: 8px !important; width: auto !important; min-width: 124px !important;
    min-height: 43px !important; height: auto !important; padding: 10px 13px !important;
    border-radius: 999px !important; font-size: .78rem !important; line-height: 1.15 !important;
    white-space: nowrap !important;
  }
  #dragDownloads .btn-float span:not(.arch-badge) { display: inline !important; visibility: visible !important; }
  #dragDownloads .btn-float i, #dragDownloads .btn-float .eml-online-icon,
  #dragDownloads .btn-float .eml-inline-icon { display: inline-block !important; width: 1.15rem !important;
    height: 1.15rem !important; font-size: 1.15rem !important; margin: 0 !important; }
  #dragWhatsapp.btn-whatsapp-float { bottom: max(16px, env(safe-area-inset-bottom, 0px)) !important;
    left: max(12px, env(safe-area-inset-left, 0px)) !important; z-index: 9998 !important; }
}
@media (max-width: 360px) { #dragDownloads .btn-float { min-width: 112px !important; padding: 9px 10px !important; } }
/* FIN EML_MOBILE_DOWNLOAD_BUTTONS_PUBLISH_V1 */
'''

def clean_local_index(index: Path) -> tuple[int, int, bool, Path | None]:
    original = index.read_text(encoding="utf-8-sig")
    doc, n_cards = clean_duplicate_feature_cards(original)
    doc, n_docs = clean_hero_doc_repeats(doc)
    css_added = False
    if "EML_MOBILE_DOWNLOAD_BUTTONS_PUBLISH_V1" not in doc:
        pos = doc.lower().rfind("</style>")
        if pos >= 0:
            doc = doc[:pos] + MOBILE_CSS + "\n" + doc[pos:]
            css_added = True
    backup = None
    if doc != original:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = index.with_name(index.name + f".backup_avant_publication_{stamp}")
        shutil.copy2(index, backup)
        index.write_text(doc, encoding="utf-8")
    # Contrôle des répétitions explicites des captures ajoutées au bloc fonctionnalités.
    captures = re.findall(r'data-eml-capture=["\'](capture_\d+_HD\.jpg)["\']', doc, re.I)
    repeated = sorted({x for x in captures if captures.count(x) > 1})
    if repeated:
        raise TaskError("Des captures HD restent répétées après nettoyage : " + ", ".join(repeated) + ". Publication annulée.")
    return n_cards, n_docs, css_added, backup

def is_ignored(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return (any(x in IGNORED_DIRS for x in rel.parts) or path.name in IGNORED_FILES
            or path.suffix.lower() in {".pyc", ".pyo"}
            or ".backup_" in path.name or path.name.endswith(".bak"))

def source_files(source: Path) -> list[Path]:
    out=[]
    for current, dirs, names in os.walk(source):
        cp=Path(current); dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in names:
            p=cp/name
            if p.is_symlink(): print(f"[AVERTISSEMENT] Lien symbolique ignoré : {p}"); continue
            if not is_ignored(p, source): out.append(p)
    return out

def backup_remote(repo_dir: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for cur, dirs, names in os.walk(repo_dir):
            cp=Path(cur); dirs[:] = [d for d in dirs if d != ".git"]
            for name in names:
                p=cp/name
                if ".git" not in p.relative_to(repo_dir).parts: z.write(p, p.relative_to(repo_dir).as_posix())

def clear_worktree(repo_dir: Path) -> None:
    for p in repo_dir.iterdir():
        if p.name.lower() == ".git": continue
        shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink(missing_ok=True)

def ensure_identity(repo_dir: Path) -> None:
    def get(key):
        p=subprocess.run(["git","config","--get",key],cwd=repo_dir,text=True,capture_output=True)
        return p.stdout.strip() if p.returncode==0 else ""
    name,email=get("user.name"),get("user.email")
    if not name: name=input("Nom d'auteur Git : ").strip()
    if not email: email=input("E-mail associé à GitHub : ").strip()
    if not name or "@" not in email: raise TaskError("Identité Git invalide. Aucun push effectué.")
    run_git(["config","user.name",name],repo_dir); run_git(["config","user.email",email],repo_dir)

def main() -> int:
    ap=argparse.ArgumentParser(description="Nettoie puis met à jour le dépôt GitHub EasyMedicaLink.")
    ap.add_argument("--source",default=DEFAULT_SOURCE)
    ap.add_argument("--repo",default=DEFAULT_REPO)
    ap.add_argument("--message",default="Nettoyage des captures et mise a jour du site EasyMedicaLink")
    ap.add_argument("--backup-dir",default=None)
    ap.add_argument("--yes",action="store_true",help="Valide sans demander le mot de confirmation.")
    args=ap.parse_args()
    source=Path(args.source).expanduser().resolve()
    index=source/"index.html"
    if not source.is_dir() or not index.is_file(): raise TaskError(f"Dossier source ou index.html introuvable : {source}")
    asset_dir = source / "asset"
    if not asset_dir.is_dir(): raise TaskError("Le dossier asset/ est absent. Publication arrêtée pour éviter un site avec images manquantes.")
    hd_captures = list(asset_dir.glob("capture_*_HD.jpg"))
    if len(hd_captures) < 10:
        raise TaskError(f"Seulement {len(hd_captures)} captures HD trouvées dans asset/. Les 10 captures sont attendues.")
    # Contrôle des chemins locaux des balises IMG avant tout push.
    html_preview = index.read_text(encoding="utf-8-sig")
    local_refs = re.findall(r'<img\b[^>]*?\bsrc\s*=\s*(["\'])(.*?)\1', html_preview, re.I | re.S)
    missing = []
    for _, ref in local_refs:
        ref = ref.strip()
        if not ref or ref.startswith(("http://", "https://", "data:", "blob:", "//", "#")):
            continue
        ref_path = (source / ref.replace("/", os.sep)).resolve()
        try:
            ref_path.relative_to(source)
        except ValueError:
            continue
        if not ref_path.is_file(): missing.append(ref)
    if missing:
        unique_missing = sorted(set(missing))
        raise TaskError("Images locales référencées mais absentes : " + ", ".join(unique_missing[:20]) + (" ..." if len(unique_missing) > 20 else "") + ". Publication annulée.")
    files=source_files(source)
    if not files: raise TaskError("Aucun fichier source à publier.")
    large=[(p,p.stat().st_size) for p in files if p.stat().st_size >= MAX_FILE_BYTES]
    if large: raise TaskError("Fichiers de 100 Mo ou plus détectés : " + ", ".join(str(p) for p,_ in large))
    print("\n=== MISE À JOUR EASYMEDICALINK ===")
    print("Source :",source); print("Dépôt :",args.repo); print("Fichiers repérés :",len(files))
    print("Nettoyage ciblé de l'index avant publication...")
    n_cards,n_docs,css_added,local_backup=clean_local_index(index)
    print(f"Cartes HD identiques retirées : {n_cards}")
    print(f"Images déjà présentées dans leur rubrique dédiées retirées du carrousel : {n_docs}")
    print("Correctif boutons mobiles ajouté :", "oui" if css_added else "déjà présent")
    if local_backup: print("Sauvegarde locale :",local_backup)
    files=source_files(source)
    temp=Path(tempfile.mkdtemp(prefix="easymedicalink_github_update_")); repo_dir=temp/"repo"
    cleanup_temp=False
    try:
        print("\n[1/5] Clonage du dépôt et détection de la branche...")
        run_git(["clone",args.repo,str(repo_dir)])
        branch=run_git(["branch","--show-current"],repo_dir,capture=True)
        if not branch: raise TaskError("Branche Git par défaut introuvable.")
        backup_root=Path(args.backup_dir).expanduser().resolve() if args.backup_dir else source.parent
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        backup=backup_root/f"Sauvegarde_depot_EasyMedicaLink_{stamp}.zip"
        print("Branche :",branch); print("Sauvegarde distante :",backup)
        if not args.yes and input("\nLe contenu distant sera remplacé par Site web2. Tapez exactement PUBLIER pour continuer : ").strip() != "PUBLIER":
            print("Publication annulée. Le dépôt distant reste inchangé."); cleanup_temp=True; return 0
        print("[2/5] Sauvegarde du dépôt distant..."); backup_remote(repo_dir,backup)
        print("[3/5] Remplacement du contenu de travail (historique Git conservé)...")
        clear_worktree(repo_dir)
        for f in files:
            rel=f.relative_to(source); target=repo_dir/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(f,target)
        if not (repo_dir/"index.html").is_file() or not (repo_dir/"asset").is_dir(): raise TaskError("Contrôle post-copie échoué. Push annulé.")
        print("[4/5] Création du commit...")
        run_git(["add","-A"],repo_dir)
        diff=subprocess.run(["git","diff","--cached","--quiet"],cwd=repo_dir,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if diff.returncode==0:
            print("Le dépôt distant contient déjà ces fichiers. Aucun commit nécessaire."); print("Sauvegarde :",backup); cleanup_temp=True; return 0
        if diff.returncode!=1: raise TaskError("Impossible de vérifier les différences Git.")
        ensure_identity(repo_dir)
        run_git(["commit","-m",args.message],repo_dir)
        print("[5/5] Envoi vers GitHub...")
        run_git(["push","origin",branch],repo_dir)
        print("\n[SUCCÈS] Dépôt mis à jour :",args.repo)
        print("Branche :",branch); print("Sauvegarde :",backup)
        print("Le dossier source local n'a pas été remplacé. Son index.html a seulement reçu le nettoyage sauvegardé.")
        cleanup_temp=True
        return 0
    finally:
        if cleanup_temp: shutil.rmtree(temp,ignore_errors=True)
        else: print("Copie temporaire conservée pour diagnostic :",temp)

if __name__=="__main__":
    try: raise SystemExit(main())
    except (TaskError,KeyboardInterrupt) as e:
        print("\n[ARRÊT]",e,file=sys.stderr)
        if isinstance(e,KeyboardInterrupt): print("Opération interrompue.",file=sys.stderr)
        raise SystemExit(130 if isinstance(e,KeyboardInterrupt) else 1)
