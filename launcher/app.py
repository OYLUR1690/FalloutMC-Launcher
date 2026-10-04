from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.error import HTTPError, URLError
from .core import VERSION, SERVER, MANIFEST_URL, InstanceLock, Updater, atomic_json, fetch_json, offline_uuid, download

BASE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'FalloutMC'
GAME, STATE = BASE/'minecraft', BASE/'state'


def install_game(status):
    import minecraft_launcher_lib as mcl
    callbacks = {'setStatus': status}
    status('Installation / vérification de Minecraft et Java 21…')
    mcl.install.install_minecraft_version('1.21.1', GAME, callback=callbacks)
    data = json.loads((GAME/'versions/1.21.1/1.21.1.json').read_text(encoding='utf-8'))
    runtime = data['javaVersion']
    if runtime['majorVersion'] != 21:
        raise RuntimeError('Java 21 attendu')
    java = mcl.runtime.get_executable_path(runtime['component'], GAME)
    if not java:
        raise RuntimeError('Installation de Java incomplète')
    check = subprocess.run([java, '-version'], capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if check.returncode or not re.search(r'version "21[.\"]', check.stderr+check.stdout):
        raise RuntimeError('Java 21 ne démarre pas correctement')
    loader = mcl.mod_loader.get_mod_loader('neoforge')
    installed = loader.get_installed_version('1.21.1', '21.1.252')
    if not (GAME/'versions'/installed/(installed+'.json')).exists():
        status('Installation de NeoForge 21.1.252…')
        loader.install('1.21.1', GAME, loader_version='21.1.252', java=java, callback=callbacks)
    else:
        status('Vérification des bibliothèques NeoForge…')
        mcl.install.install_minecraft_version(installed, GAME, callback=callbacks)
    return installed, java


def self_update(manifest, status):
    item = manifest.get('launcher')
    if not item or item.get('version') == VERSION:
        return False
    from .core import check_url
    if not re.fullmatch(r'\d+\.\d+\.\d+', item.get('version','')):
        raise ValueError('Version du launcher invalide')
    new = tuple(map(int, item['version'].split('.')))
    if new <= tuple(map(int, VERSION.split('.'))):
        return False
    if not getattr(sys, 'frozen', False) or os.name != 'nt':
        raise RuntimeError('Une mise à jour du launcher est nécessaire : télécharger la nouvelle version depuis GitHub Releases.')
    if not re.fullmatch('[a-f0-9]{64}', item.get('sha256','')) or type(item.get('size')) is not int or not 0 < item['size'] <= 200*1024*1024:
        raise ValueError('Mise à jour du launcher invalide')
    check_url(item['url'])
    update = STATE/'launcher-update'
    update.mkdir(parents=True, exist_ok=True)
    target = update/'FalloutMC-Launcher-new.exe'
    status('Mise à jour du launcher…')
    download(item['url'], target, item['sha256'], item['size'], status)
    script = update/'replace.ps1'
    script.write_text('''param([int]$ParentId, [string]$Source, [string]$Target)
$ErrorActionPreference = "Stop"
try {
    Wait-Process -Id $ParentId -ErrorAction SilentlyContinue
    $Staged = $Target + ".new"
    $Backup = $Target + ".old"
    Copy-Item -LiteralPath $Source -Destination $Staged -Force
    $Replaced = $false
    for ($Try = 0; $Try -lt 30; $Try++) {
        try {
            if (Test-Path -LiteralPath $Backup) { Remove-Item -LiteralPath $Backup -Force }
            Move-Item -LiteralPath $Target -Destination $Backup -Force
            try { Move-Item -LiteralPath $Staged -Destination $Target -Force }
            catch { Move-Item -LiteralPath $Backup -Destination $Target -Force; throw }
            $Replaced = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $Replaced) { throw "Impossible de remplacer le launcher" }
    Start-Process -FilePath $Target
} catch { $_ | Out-String | Set-Content -LiteralPath ($Source + ".error.txt") }
''', encoding='utf-8-sig')
    subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),
                      '-ParentId',str(os.getpid()),'-Source',str(target),'-Target',sys.executable],
                     creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
    return True


class App:
    def __init__(self, root):
        self.root, self.events, self.running = root, queue.Queue(), False
        self.process = None
        STATE.mkdir(parents=True,exist_ok=True)
        logging.basicConfig(filename=STATE/'launcher.log', level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
        try:
            self.lock = InstanceLock(STATE)
        except RuntimeError as e:
            messagebox.showerror('FalloutMC',str(e)); root.destroy(); return
        root.title('FalloutMC — Launcher')
        root.geometry('640x480'); root.minsize(600,450)
        root.configure(bg='#111a15')
        style = ttk.Style(); style.theme_use('clam')
        style.configure('TFrame', background='#111a15')
        style.configure('TLabel', background='#111a15', foreground='#c5d9c5', font=('Segoe UI',11))
        style.configure('Title.TLabel', foreground='#b3eb72',font=('Segoe UI',30,'bold'))
        style.configure('TButton',font=('Segoe UI',12,'bold'),padding=10)
        style.configure('TCheckbutton',background='#111a15',foreground='#c5d9c5')
        frame=ttk.Frame(root,padding=28);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='FALLOUTMC',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Survis. Explore. Reconstruis.').pack(anchor='w',pady=(0,20))
        settings={}
        try:settings=json.loads((STATE/'settings.json').read_text(encoding='utf-8'))
        except (FileNotFoundError,ValueError):pass
        self.name=tk.StringVar(value=settings.get('username',''))
        self.memory=tk.IntVar(value=settings.get('memory',6))
        ttk.Label(frame,text='Pseudo Minecraft (respecte les majuscules)').pack(anchor='w')
        self.entry=ttk.Entry(frame,textvariable=self.name,font=('Segoe UI',13));self.entry.pack(fill='x',pady=5)
        row=ttk.Frame(frame);row.pack(fill='x',pady=10)
        ttk.Label(row,text='Mémoire du jeu :').pack(side='left')
        self.spin=ttk.Spinbox(row,from_=2,to=24,width=4,textvariable=self.memory);self.spin.pack(side='left',padx=8)
        ttk.Label(row,text='Go').pack(side='left')
        ttk.Label(frame,text='Le mot de passe EasyLogin se saisit uniquement en jeu.',wraplength=570).pack(anchor='w',pady=5)
        self.play=ttk.Button(frame,text='Jouer à FalloutMC',command=self.start);self.play.pack(fill='x',pady=15)
        self.progress=ttk.Progressbar(frame,mode='indeterminate');self.progress.pack(fill='x')
        self.status=tk.StringVar(value='Prêt — vérification des mises à jour avant chaque lancement.')
        ttk.Label(frame,textvariable=self.status,wraplength=570).pack(anchor='w',pady=10)
        ttk.Label(frame,text=f'{SERVER}  •  Launcher {VERSION}',font=('Segoe UI',9)).pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(100,self.pump)

    def pump(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='status':self.status.set(value)
                elif kind=='error':
                    self.finish();messagebox.showerror('FalloutMC',value)
                elif kind=='done':self.finish();self.status.set(value)
                elif kind=='restart':
                    self.lock.close();self.root.destroy();return
        except queue.Empty:pass
        self.root.after(100,self.pump)

    def finish(self):
        self.running=False;self.progress.stop();self.play.configure(state='normal')
        self.entry.configure(state='normal');self.spin.configure(state='normal')

    def start(self):
        name=self.name.get().strip()
        if not re.fullmatch(r'[A-Za-z0-9_]{3,16}',name):
            messagebox.showerror('Pseudo','Utilise 3 à 16 lettres, chiffres ou underscores.');return
        try:memory=int(self.memory.get())
        except (ValueError,tk.TclError):memory=0
        if not 2 <= memory <= 24:
            messagebox.showerror('Mémoire','Choisis entre 2 et 24 Go, en laissant de la mémoire pour Windows.');return
        atomic_json(STATE/'settings.json',{'username':name,'memory':memory})
        self.running=True;self.play.configure(state='disabled');self.entry.configure(state='disabled');self.spin.configure(state='disabled')
        self.progress.start(15)
        threading.Thread(target=self.work,args=(name,memory),daemon=True).start()

    def work(self,name,memory):
        notify=lambda text:self.events.put(('status',text))
        try:
            updater=Updater(GAME,STATE,notify)
            updater.recover()
            notify('Recherche de la version active…')
            manifest=fetch_json(MANIFEST_URL)
            from .core import validate_manifest
            validate_manifest(manifest)
            if self_update(manifest,notify):
                self.events.put(('restart',None));return
            updater.sync(manifest)
            installed,java=install_game(notify)
            import minecraft_launcher_lib as mcl
            command=mcl.command.get_minecraft_command(installed,GAME,{
                'username':name,'uuid':offline_uuid(name),'token':'0',
                'executablePath':java,'launcherName':'FalloutMC','launcherVersion':VERSION,
                'jvmArguments':['-Xms1G',f'-Xmx{memory}G'], 'gameDirectory':str(GAME)})
            notify('Minecraft est lancé. Authentifie-toi avec EasyLogin en jeu.')
            with open(STATE/'game-output.log','w',encoding='utf-8') as output:
                self.process=subprocess.Popen(command,cwd=GAME,stdout=output,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                code=self.process.wait();self.process=None
            if code:
                raise RuntimeError(f'Minecraft s’est arrêté avec le code {code}. Le journal est dans {STATE / "game-output.log"}.')
            self.events.put(('done','Jeu fermé — prêt pour une nouvelle vérification.'))
        except HTTPError as e:
            text='Aucune version du pack publiée pour le moment.' if e.code==404 else f'Service de téléchargement indisponible (HTTP {e.code}).'
            self.events.put(('error',text+' Le jeu ne sera pas lancé.'))
        except (URLError,TimeoutError) as e:
            logging.exception('Network error');self.events.put(('error','Connexion impossible. Vérifie Internet puis réessaie.'))
        except Exception as e:
            logging.exception('Launch failed');self.events.put(('error',str(e)))

    def close(self):
        if self.running:
            messagebox.showinfo('FalloutMC','Attends la fin de la mise à jour ou ferme Minecraft avant de fermer le launcher.');return
        self.lock.close();self.root.destroy()


def main():
    root=tk.Tk();App(root);root.mainloop()
