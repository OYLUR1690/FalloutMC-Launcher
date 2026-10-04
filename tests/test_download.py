from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from launcher.core import download, digest, InstanceLock
import hashlib

class Response(BytesIO):
    def geturl(self):return 'https://example.org/file'

class DownloadTests(unittest.TestCase):
    def test_valid_download_and_reject_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'asset.jar'
            good=b'expected'
            sha=hashlib.sha256(good).hexdigest()
            with patch('urllib.request.urlopen',return_value=Response(good)):
                download('https://example.org/file',path,sha,len(good))
            self.assertEqual(digest(path),sha)
            for content in [b'bad',b'xxxxxxxx',b'oversized data']:
                with self.subTest(content=content),patch('urllib.request.urlopen',return_value=Response(content)):
                    with self.assertRaises(ValueError):download('https://example.org/file',path,sha,len(good))
                self.assertEqual(path.read_bytes(),good)
                self.assertFalse(path.with_suffix('.jar.part').exists())
    def test_reject_non_https(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):download('http://example.org',Path(directory)/'a','a'*64,0)
    def test_one_instance_only(self):
        with tempfile.TemporaryDirectory() as directory:
            lock=InstanceLock(Path(directory))
            try:
                with self.assertRaises(RuntimeError):InstanceLock(Path(directory))
            finally:lock.close()
            another=InstanceLock(Path(directory));another.close()

if __name__=='__main__':unittest.main()
