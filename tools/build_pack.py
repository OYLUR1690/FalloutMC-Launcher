"""Build immutable release assets locally; never uploads anything."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
if not getattr(sys,'frozen',False):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from launcher.core import OWNER, REPOSITORY, VERSION, SERVER, digest, safe_path, validate_manifest, atomic_json, check_url


def build(client, menu, launcher, tag, output, config_selection=None, remote_sources=None):
    client, menu, launcher, output = map(Path,(client,menu,launcher,output))
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',tag):
        raise ValueError('Nom de version invalide')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choisis un dossier de sortie vide pour éviter de mélanger les versions')
    if output.resolve().is_relative_to(client.resolve()):
        raise ValueError('Le dossier de sortie doit être hors du dossier client')
    if not menu.is_file() or not menu.name.startswith('falloutmc-menu-') or menu.suffix != '.jar':
        raise ValueError('Sélectionne le JAR compilé du menu FalloutMC')
    if not launcher.is_file() or launcher.suffix.lower() != '.exe':
        raise ValueError('Sélectionne FalloutMC-Launcher.exe compilé')
    candidates={}
    for directory in ['mods','kubejs/assets','kubejs/startup_scripts','kubejs/client_scripts']:
        base=client/directory
        if not base.exists():continue
        for file in sorted(base.rglob('*')):
            relative=file.relative_to(client).as_posix()
            safe_path(client,relative)
            if not file.is_file():continue
            if directory=='mods' and (file.suffix != '.jar' or file.name.startswith('falloutmc-menu-')):continue
            candidates[relative]=(file,'managed')
    if not any(name.startswith('mods/') for name in candidates):
        raise ValueError('Le dossier client ne contient aucun mod')
    if 'kubejs/startup_scripts/falloutmc_banknotes.js' not in candidates:
        raise ValueError('Le script des billets manque au dossier client')
    for n in (1,10,100,1000,10000,100000):
        if f'kubejs/assets/kubejs/textures/item/credit_{n}.png' not in candidates:
            raise ValueError('Une texture de billet manque')
    # Configs must be selected individually; never export server configuration wholesale.
    for item in config_selection or []:
        name=item['path']
        if not name.startswith(('config/','defaultconfigs/','kubejs/config/')):
            raise ValueError('Sélection de configuration invalide')
        if any(word in name.casefold() for word in ('easylogin','players.json','password','secret','web_server')):
            raise ValueError('Fichier d’authentification ou secret exclu')
        file=safe_path(client,name)
        if not file.is_file():raise ValueError('Configuration absente : '+name)
        candidates[name]=(file,item.get('policy','managed'))
    candidates['mods/'+menu.name]=(menu,'managed')
    output.mkdir(parents=True,exist_ok=True)
    url=f'https://github.com/{OWNER}/{REPOSITORY}/releases/download/{tag}/'
    items=[]
    remote_sources=remote_sources or {}
    for name,(file,policy) in sorted(candidates.items()):
        sha=digest(file);asset=sha+'.bin'
        source=remote_sources.get(name)
        if source:
            source=check_url(source)
        else:
            shutil.copyfile(file,output/asset)
            source=url+asset
        items.append({'path':name,'size':file.stat().st_size,'sha256':sha,'url':source,'policy':policy})
    exe=output/'FalloutMC-Launcher.exe';shutil.copyfile(launcher,exe)
    data={'schemaVersion':1,'release':tag,'minecraft':'1.21.1','neoforge':'21.1.252','server':SERVER,
          'launcher':{'version':VERSION,'size':exe.stat().st_size,'sha256':digest(exe),'url':url+exe.name},
          'files':items}
    validate_manifest(data);atomic_json(output/'pack.json',data)
    return data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--client');parser.add_argument('--menu');parser.add_argument('--launcher')
    parser.add_argument('--tag');parser.add_argument('--output')
    parser.add_argument('--configs',help='JSON local : liste des seuls fichiers de configuration client sélectionnés')
    parser.add_argument('--sources',help='JSON local : correspondance chemin -> URL officielle pour éviter de republier les mods')
    args=parser.parse_args()
    if not all([args.client,args.menu,args.launcher,args.tag,args.output]):
        import tkinter as tk
        from tkinter import filedialog,simpledialog,messagebox
        root=tk.Tk();root.withdraw()
        try:
            args.client=filedialog.askdirectory(title='Dossier client FalloutMC (mods et kubejs)')
            if not args.client:return
            args.menu=filedialog.askopenfilename(title='Mod du menu compilé',filetypes=[('Java mod','*.jar')])
            if not args.menu:return
            args.launcher=filedialog.askopenfilename(title='Launcher compilé',filetypes=[('Launcher','*.exe')])
            if not args.launcher:return
            args.tag=simpledialog.askstring('Version','Nom unique, par exemple pack-2026.10.04.1')
            if not args.tag:return
            args.output=filedialog.askdirectory(title='Dossier vide où préparer la publication')
            if not args.output:return
            configs=json.loads(Path(args.configs).read_text(encoding='utf-8')) if args.configs else None
            sources=json.loads(Path(args.sources).read_text(encoding='utf-8')) if args.sources else None
            data=build(args.client,args.menu,args.launcher,args.tag,args.output,configs,sources)
            messagebox.showinfo('FalloutMC',f"Version {args.tag} préparée : {len(data['files'])} fichiers.\nAucun fichier n’a été envoyé.\nLa publication reste à faire sur GitHub Releases.")
        except Exception as e:messagebox.showerror('Préparation du pack',str(e))
        finally:root.destroy()
    else:
        configs=json.loads(Path(args.configs).read_text(encoding='utf-8')) if args.configs else None
        sources=json.loads(Path(args.sources).read_text(encoding='utf-8')) if args.sources else None
        data=build(args.client,args.menu,args.launcher,args.tag,args.output,configs,sources)
        print(f"Prepared {len(data['files'])} files in {args.output}; nothing uploaded")

if __name__=='__main__':main()
