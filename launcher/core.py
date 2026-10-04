"""Verified, recoverable updates for a dedicated FalloutMC instance."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import urllib.request
import uuid

OWNER = 'OYLUR1690'
REPOSITORY = 'FalloutMC-Launcher'
MANIFEST_URL = f'https://github.com/{OWNER}/{REPOSITORY}/releases/latest/download/pack.json'
VERSION = '0.1.0'
SERVER = '116.202.116.207:25565'
ROOTS = {'mods', 'config', 'defaultconfigs', 'kubejs'}
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}


def offline_uuid(name):
    raw = bytearray(hashlib.md5(('OfflinePlayer:' + name).encode()).digest())
    raw[6] = (raw[6] & 15) | 48
    raw[8] = (raw[8] & 63) | 128
    return str(uuid.UUID(bytes=bytes(raw)))


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError('Chemin de fichier interdit')
    parts = relative.split('/')
    if not parts or parts[0] not in ROOTS or any(not p or p in {'.', '..'} for p in parts):
        raise ValueError('Chemin hors du pack client')
    for p in parts:
        if p.endswith((' ', '.')) or any(ord(c) < 32 or c in '<>"|?*' for c in p) or p.split('.')[0].upper() in RESERVED:
            raise ValueError('Nom de fichier incompatible avec Windows')
    result = root.joinpath(*parts)
    current = root
    for p in parts:
        current = current / p
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise ValueError('Lien de fichier interdit dans le pack')
    result.resolve().relative_to(root.resolve())
    return result


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def check_url(url):
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Un téléchargement HTTPS est requis')
    return url


def fetch_json(url):
    req = urllib.request.Request(check_url(url), headers={'User-Agent': 'FalloutMC-Launcher/'+VERSION})
    with urllib.request.urlopen(req, timeout=30) as response:
        check_url(response.geturl())
        data = response.read(8*1024*1024+1)
    if len(data) > 8*1024*1024:
        raise ValueError('Fichier de mise à jour trop volumineux')
    return json.loads(data)


def download(url, target, expected_sha, expected_size, status=lambda _: None):
    check_url(url)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix+'.part')
    h, size = hashlib.sha256(), 0
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'FalloutMC-Launcher/'+VERSION})
        with urllib.request.urlopen(req, timeout=60) as response, open(partial, 'wb') as out:
            check_url(response.geturl())
            for block in iter(lambda: response.read(1024*1024), b''):
                size += len(block)
                if size > expected_size:
                    raise ValueError('Taille reçue supérieure à la taille attendue')
                out.write(block)
                h.update(block)
                status(f'Téléchargement : {size // 1024} / {expected_size // 1024} Ko')
            out.flush()
            os.fsync(out.fileno())
        if size != expected_size or h.hexdigest() != expected_sha:
            raise ValueError('Fichier incomplet ou empreinte incorrecte')
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)


def validate_manifest(data):
    if data.get('schemaVersion') != 1 or not isinstance(data.get('release'), str) or not data['release']:
        raise ValueError('Version du pack invalide')
    if data.get('minecraft') != '1.21.1' or data.get('neoforge') != '21.1.252':
        raise ValueError('Cette version du launcher attend Minecraft 1.21.1 / NeoForge 21.1.252')
    if data.get('server') != SERVER:
        raise ValueError('Adresse du serveur inattendue')
    files = data.get('files')
    if not isinstance(files, list) or not files or len(files) > 10000:
        raise ValueError('Liste de fichiers du pack invalide')
    names = set()
    for item in files:
        safe_path(Path('/validation'), item['path'])
        key = item['path'].casefold()
        if key in names:
            raise ValueError('Deux fichiers ont le même nom')
        names.add(key)
        if item.get('policy', 'managed') not in {'managed', 'initial'}:
            raise ValueError('Politique de configuration invalide')
        if not re.fullmatch('[a-f0-9]{64}', item.get('sha256', '')):
            raise ValueError('Empreinte SHA-256 invalide')
        if type(item.get('size')) is not int or not 0 <= item['size'] <= 2*1024**3:
            raise ValueError('Taille de fichier invalide')
        check_url(item['url'])
    if not any(i['path'].startswith('mods/falloutmc-menu-') for i in files):
        raise ValueError('Le mod du menu FalloutMC manque au pack')
    return data


class InstanceLock:
    def __init__(self, state):
        state.mkdir(parents=True, exist_ok=True)
        self.stream = open(state/'instance.lock', 'a+b')
        self.stream.seek(0)
        self.stream.write(b'0')
        self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError):
            self.stream.close()
            raise RuntimeError('FalloutMC est déjà ouvert sur ce PC')
    def close(self):
        self.stream.close()


class Updater:
    def __init__(self, game: Path, state: Path, status=lambda _: None, downloader=download):
        self.game, self.state, self.status, self.downloader = game, state, status, downloader
        self.game.mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        self.journal = self.state/'transaction.json'
        self.record = self.state/'managed.json'
        self.tx = self.state/'transaction'

    def recover(self):
        if not self.journal.exists():
            return
        data = json.loads(self.journal.read_text(encoding='utf-8'))
        if not data.get('committed'):
            self.status('Restauration de la mise à jour interrompue…')
            for op in reversed(data['operations']):
                dest = safe_path(self.game, op['path'])
                backup = safe_path(self.tx/'backup', op['path'])
                if backup.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(backup, dest)
                elif not op['existed']:
                    dest.unlink(missing_ok=True)
            if data['oldState'] is None:
                self.record.unlink(missing_ok=True)
            else:
                atomic_json(self.record, data['oldState'])
        else:
            # Keep the previous managed files and quarantined extra mods for recovery.
            backup = self.tx/'backup'
            if backup.exists():
                archive = self.state/'backups'/uuid.uuid4().hex
                archive.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(backup), str(archive))
        self.journal.unlink()
        shutil.rmtree(self.tx, ignore_errors=True)

    def sync(self, manifest):
        validate_manifest(manifest)
        self.recover()
        old = json.loads(self.record.read_text(encoding='utf-8')) if self.record.exists() else None
        previous = {x['path']:x for x in (old or {}).get('files', [])}
        current = {x['path']:x for x in manifest['files']}
        # Validate old local state before allowing removals.
        for name in previous:
            safe_path(self.game, name)
        shutil.rmtree(self.tx, ignore_errors=True)
        changes = []
        for name, item in current.items():
            dest = safe_path(self.game, name)
            if item.get('policy') == 'initial' and dest.exists():
                continue
            if dest.is_file() and dest.stat().st_size == item['size'] and digest(dest) == item['sha256']:
                self.status('Vérifié : '+name)
                continue
            staged = safe_path(self.tx/'download', name)
            self.status('Préparation : '+name)
            self.downloader(item['url'], staged, item['sha256'], item['size'], self.status)
            changes.append({'path':name, 'existed':dest.exists(), 'replace':True})
        current_keys = {name.casefold() for name in current}
        removals = {name for name, item in previous.items() if name.casefold() not in current_keys and item.get('policy','managed') == 'managed'}
        # This instance belongs only to FalloutMC; extra jars are moved to a backup.
        mods = self.game/'mods'
        if mods.exists():
            for jar in mods.glob('*.jar'):
                relative = jar.relative_to(self.game).as_posix()
                safe_path(self.game, relative)
                if relative.casefold() not in current_keys:
                    removals.add(relative)
        for name in sorted(removals):
            dest = safe_path(self.game, name)
            if dest.exists():
                changes.append({'path':name, 'existed':True, 'replace':False})
        journal = {'oldState':old, 'operations':changes, 'committed':False}
        atomic_json(self.journal, journal)
        try:
            for op in changes:
                dest = safe_path(self.game, op['path'])
                if op['existed']:
                    backup = safe_path(self.tx/'backup', op['path'])
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(dest, backup)
                if op['replace']:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(safe_path(self.tx/'download', op['path']), dest)
            for item in manifest['files']:
                dest = safe_path(self.game,item['path'])
                if item.get('policy') != 'initial' and (not dest.is_file() or digest(dest) != item['sha256']):
                    raise RuntimeError('Échec de vérification finale : '+item['path'])
            atomic_json(self.record, {'release':manifest['release'], 'files':manifest['files']})
            journal['committed'] = True
            atomic_json(self.journal, journal)
        except Exception:
            self.recover()
            raise
        self.recover()
        self.status('Pack '+manifest['release']+' prêt')
