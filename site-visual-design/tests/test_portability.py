"""隔离离线验证；不读取用户配置，不调用真实 API 或浏览器。"""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace


def subprocess_stub(**kwargs):
    return SimpleNamespace(run=Mock(**kwargs), TimeoutExpired=subprocess.TimeoutExpired)

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT.parent / 'svg-lecture-deck' / 'scripts'
sys.path.insert(0, str(SVG))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

api = load('image_api_test', ROOT / 'scripts/image_api.py')
mockup = load('mockup_test', ROOT / 'scripts/mockup.py')
import canvas
import svg2png

class OfflineTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '_local').mkdir(exist_ok=True)
        self.d = Path(tempfile.mkdtemp(dir=ROOT / '_local'))
        api.CONFIG_PATH = self.d / 'config.json'
        api.LEGACY_CONFIG_PATH = self.d / 'legacy.json'
        api.ALLOW_LEGACY_CONFIG = False
        api.OVERWRITE = False
        api.NO_PROXY = None

    # 临时产物保留在 _local，不删除已有用户文件。

    def test_legacy_opt_in_and_cli_config(self):
        api.LEGACY_CONFIG_PATH.write_text(json.dumps({'api_key':'fake-key'}))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(api.resolve('sub')[2], '')
            api.ALLOW_LEGACY_CONFIG = True
            self.assertEqual(api.resolve('sub')[2], 'fake-key')
            api.main(['--config', str(self.d/'isolated.json'), 'build', '--model', 'test', '--prompt', 'test', '--out', str(self.d/'request.json')])
            self.assertEqual(api.CONFIG_PATH, self.d/'isolated.json')

    def test_proxy_and_no_sidecar(self):
        done = subprocess.CompletedProcess([], 0, b'{}\n__HTTP__200', b'')
        stub = subprocess_stub(return_value=done)
        with patch.object(api, 'subprocess', stub):
            run = stub.run
            api.curl_json('POST', 'https://example.invalid', 'fake', {'x':1}, out_file=self.d/'response')
            self.assertNotIn('--noproxy', run.call_args.args[0])
            self.assertEqual(run.call_args.kwargs['input'], b'{"x": 1}')
            self.assertFalse((self.d/'response.req.json').exists())
            api.NO_PROXY = 'example.invalid'
            api.curl_json('GET', 'https://example.invalid', 'fake')
            self.assertIn('--noproxy', run.call_args.args[0])

    def test_existing_output_unchanged(self):
        out = self.d/'request.json'
        out.write_bytes(b'original')
        with self.assertRaises(SystemExit):
            api.main(['--config', str(api.CONFIG_PATH), 'build', '--out', str(out)])
        self.assertEqual(out.read_bytes(), b'original')
        spec = self.d/'spec.json'
        spec.write_text('{"name":"test","pages":[]}')
        with self.assertRaises(SystemExit):
            mockup.cmd_scaffold(type('Args', (), {'spec':str(spec), 'out':str(self.d), 'img_dir':None})())
        self.assertEqual(out.read_bytes(), b'original')

    def test_font_missing(self):
        from PIL import Image
        image = self.d/'in.png'
        Image.new('RGB', (20,20)).save(image)
        with patch.object(api, 'die', side_effect=RuntimeError) as die:
            with self.assertRaises(RuntimeError):
                api.main(['--config', str(api.CONFIG_PATH), 'overlay', '--image', str(image), '--text', 'test', '--font', str(self.d/'missing.ttf')])
            self.assertIn('--font', die.call_args.args[0])

    def test_canvas_custom(self):
        self.assertEqual(canvas.resolve({'preset':'custom','width':1441,'height':1081}), (1440,1080))
        for value in [0,-2,1]:
            with self.assertRaises(ValueError):
                canvas.resolve({'preset':'custom','width':value,'height':100})
        with self.assertRaises(ValueError):
            canvas.resolve({'preset':'custom'})

    def test_render_new_file_returncode_and_overwrite(self):
        svg = self.d/'a.svg'
        svg.write_text('<svg/>')
        out = self.d/'a.png'
        out.write_bytes(b'original')
        with self.assertRaises(SystemExit):
            svg2png.render('fake', svg, out, 2, 2, 1)
        with patch.object(svg2png, 'subprocess', subprocess_stub(return_value=subprocess.CompletedProcess([],1,'','fail'))):
            self.assertFalse(svg2png.render('fake', svg, out, 2,2,1,True))
        self.assertEqual(out.read_bytes(), b'original')
        def render(cmd, **kwargs):
            p = Path(next(x.split('=',1)[1] for x in cmd if x.startswith('--screenshot=')))
            p.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\0'*8 + struct.pack('>II',2,2))
            return subprocess.CompletedProcess(cmd,0,'','')
        with patch.object(svg2png, 'subprocess', subprocess_stub(side_effect=render)):
            self.assertTrue(svg2png.render('fake', svg, out, 2,2,1,True))

    def test_browser_path_and_ppt_existing(self):
        with patch.object(svg2png.shutil, 'which', return_value=str(Path(sys.executable))):
            self.assertEqual(svg2png.find_browser('configured-browser'), str(Path(sys.executable)))
        out = self.d/'old.pptx'
        out.write_bytes(b'original')
        result = subprocess.run([sys.executable,'-B',str(SVG/'svg2pptx.py'),'--out',str(out),'--svg-dir',str(self.d)], capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(out.read_bytes(),b'original')

if __name__ == '__main__':
    unittest.main(verbosity=2)
