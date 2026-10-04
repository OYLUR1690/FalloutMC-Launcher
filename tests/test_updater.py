import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from launcher.core import Updater, safe_path, offline_uuid, atomic_json, validate_manifest


def entry(name, content, policy='managed'):
    return {'path':name,'size':len(content),'sha256':hashlib.sha256(content).hexdigest(),
            'url':'https://example.org/'+name,'policy':policy}


def manifest(*items):
    return {'schemaVersion':1,'release':'test','minecraft':'1.21.1','neoforge':'21.1.252',
            'server':'116.202.116.207:25565',
            'files':[entry('mods/falloutmc-menu-0.1.0.jar',b'menu'),*items]}


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.game=self.root/'game';self.state=self.root/'state';self.calls=[]
        def fetch(url,path,sha,size,status):
            self.calls.append(url);path.parent.mkdir(parents=True,exist_ok=True)
            content=self.content[sha]
            path.write_bytes(content)
        self.content={hashlib.sha256(x).hexdigest():x for x in [b'menu',b'new',b'new2',b'initial']}
        self.updater=Updater(self.game,self.state,downloader=fetch)
    def tearDown(self):self.tmp.cleanup()
    def put(self,name,content):
        path=self.game/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    def test_offline_identity(self):
        self.assertEqual(offline_uuid('OYLUR'),'76318c2c-dd5f-3740-9eb1-466b64646470')
        self.assertNotEqual(offline_uuid('oylur'),offline_uuid('OYLUR'))
    def test_repair_and_no_repeated_download(self):
        m=manifest(entry('kubejs/startup_scripts/test.js',b'new'))
        self.updater.sync(m);self.assertEqual(len(self.calls),2)
        self.updater.sync(m);self.assertEqual(len(self.calls),2)
        self.put('kubejs/startup_scripts/test.js',b'bad')
        self.updater.sync(m);self.assertEqual(len(self.calls),3)
        self.assertEqual((self.game/'kubejs/startup_scripts/test.js').read_bytes(),b'new')
    def test_remove_only_managed_and_quarantine_extra_mod(self):
        self.updater.sync(manifest(entry('config/owned.json',b'new')))
        self.put('config/personal.json',b'personal');self.put('mods/extra.jar',b'extra')
        self.put('options.txt',b'options');self.put('screenshots/a.png',b'png')
        self.updater.sync(manifest())
        self.assertFalse((self.game/'config/owned.json').exists())
        self.assertFalse((self.game/'mods/extra.jar').exists())
        self.assertEqual((self.game/'config/personal.json').read_bytes(),b'personal')
        self.assertEqual((self.game/'options.txt').read_bytes(),b'options')
        self.assertTrue(list((self.state/'backups').rglob('extra.jar')))
    def test_initial_settings_preserved(self):
        self.put('config/personal.json',b'personal')
        self.updater.sync(manifest(entry('config/personal.json',b'initial','initial')))
        self.assertEqual((self.game/'config/personal.json').read_bytes(),b'personal')
    def test_failed_download_changes_nothing(self):
        self.updater.sync(manifest(entry('config/a.json',b'new')))
        before=self.updater.record.read_bytes()
        def fail(*args):raise OSError('Interrupted network')
        self.updater.downloader=fail
        with self.assertRaises(OSError):self.updater.sync(manifest(entry('config/a.json',b'new2')))
        self.assertEqual((self.game/'config/a.json').read_bytes(),b'new')
        self.assertEqual(self.updater.record.read_bytes(),before)
    def test_failed_commit_rolls_back(self):
        self.updater.sync(manifest(entry('config/a.json',b'new')))
        before=self.updater.record.read_bytes()
        import os
        replace=os.replace
        def fail(source,dest):
            if 'download' in str(source) and str(dest).endswith('a.json'):
                raise OSError('Disk write failed')
            return replace(source,dest)
        with patch('launcher.core.os.replace',side_effect=fail):
            with self.assertRaises(OSError):self.updater.sync(manifest(entry('config/a.json',b'new2')))
        self.assertEqual((self.game/'config/a.json').read_bytes(),b'new')
        self.assertEqual(self.updater.record.read_bytes(),before)
    def test_crash_recovery(self):
        self.put('config/a.json',b'old')
        old={'release':'old','files':[entry('config/a.json',b'old')]}
        atomic_json(self.updater.record,old)
        backup=self.updater.tx/'backup/config/a.json';backup.parent.mkdir(parents=True);backup.write_bytes(b'old')
        self.put('config/a.json',b'new');self.put('config/added.json',b'new')
        atomic_json(self.updater.record,{'release':'bad','files':[]})
        atomic_json(self.updater.journal,{'oldState':old,'committed':False,'operations':[
            {'path':'config/a.json','existed':True,'replace':True},
            {'path':'config/added.json','existed':False,'replace':True}]})
        self.updater.recover()
        self.assertEqual((self.game/'config/a.json').read_bytes(),b'old')
        self.assertFalse((self.game/'config/added.json').exists())
        self.assertEqual(json.loads(self.updater.record.read_text()),old)
    def test_path_attacks(self):
        for name in ['../x','mods/../../x','mods/C:/x','mods\\x','mods//x','mods/CON.jar','mods/x.','mods/a:b','options.txt','/mods/x']:
            with self.subTest(name=name),self.assertRaises(ValueError):safe_path(self.game,name)
        (self.game/'mods').mkdir()
        try:(self.game/'mods/link').symlink_to(self.root/'outside')
        except OSError:return # Windows may disallow symlinks without developer mode
        with self.assertRaises(ValueError):safe_path(self.game,'mods/link/evil.jar')
    def test_case_collision_and_missing_menu(self):
        with self.assertRaises(ValueError):validate_manifest(manifest(entry('mods/A.jar',b'new'),entry('mods/a.jar',b'new')))
        m=manifest();m['files']=[]
        with self.assertRaises(ValueError):validate_manifest(m)

if __name__=='__main__':unittest.main()
