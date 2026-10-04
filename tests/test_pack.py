from pathlib import Path
import tempfile
import unittest
from tools.build_pack import build
from launcher.core import validate_manifest

class PackTests(unittest.TestCase):
    def test_selected_assets_only_and_remote_mod_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);client=root/'client'
            def put(name,data=b'data'):
                p=client/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            put('mods/content.jar');put('kubejs/startup_scripts/falloutmc_banknotes.js')
            for number in [1,10,100,1000,10000,100000]:put(f'kubejs/assets/kubejs/textures/item/credit_{number}.png')
            put('config/easylogin/players.json',b'secret');put('options.txt',b'personal')
            put('kubejs/config/web_server.json',b'secret');put('kubejs/startup_scripts/main.js')
            menu=root/'falloutmc-menu-0.1.0.jar';menu.write_bytes(b'menu')
            launcher=root/'FalloutMC-Launcher.exe';launcher.write_bytes(b'exe')
            result=build(client,menu,launcher,'pack-test',root/'out',remote_sources={'mods/content.jar':'https://example.org/content.jar'})
            names=[x['path'] for x in result['files']]
            self.assertEqual(len(names),10)
            self.assertNotIn('config/easylogin/players.json',names)
            self.assertNotIn('kubejs/config/web_server.json',names)
            self.assertNotIn('options.txt',names)
            self.assertIn('kubejs/startup_scripts/main.js',names)
            validate_manifest(result)
            self.assertTrue((root/'out/pack.json').is_file())
            with self.assertRaises(ValueError):build(client,menu,launcher,'pack-test',root/'out')

if __name__=='__main__':unittest.main()
