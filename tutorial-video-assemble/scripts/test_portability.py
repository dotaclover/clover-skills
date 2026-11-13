"""离线安全回归；临时输入输出仅位于仓库 _local。"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = load('build_test', HERE / 'build_film.py')
record = load('record_test', HERE / 'record_window.py')
svg = load('svg_test', HERE / 'svg2png.py')
init = load('init_test', HERE.parent.parent / 'tutorial-series-plan/scripts/init_project.py')


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        local = ROOT / '_local'
        local.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='tutorial-test-', dir=local)
        self.base = Path(self.tmp.name)
        self.ep = self.base / 'random-project' / 'episodes' / 'EP01'
        self.ep.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, cfg, *extra):
        source = self.ep / 'beats.json'
        source.write_text(json.dumps(cfg), encoding='utf-8')
        original = source.read_bytes()
        argv = ['build', '--ep', str(self.ep), '--work-dir', str(self.base / 'work'), *extra]
        with patch.object(sys, 'argv', argv), patch.object(build, 'find_bin', return_value='mock'), patch.object(build, 'run') as run:
            result = build.main()
        self.assertEqual(source.read_bytes(), original)
        run.assert_not_called()
        return result

    def test_random_root_custom_canvas_offline_voice(self):
        (self.ep / 'rec').mkdir()
        (self.ep / 'rec' / 'demo.mp4').write_bytes(b'video')
        (self.ep / 'voice.wav').write_bytes(b'audio')
        cfg = {'episode': 'EP01', 'canvas': {'preset': 'custom', 'width': 1440, 'height': 1080},
               'beats': [{'id': 'd1', 'kind': 'demo', 'src': 'demo.mp4', 'end': 5,
                          'text': '离线台词', 'voice_file': 'voice.wav'}]}
        with patch.object(build, 'duration', side_effect=[1.0, 5.0]), patch.object(build, 'make_voice', side_effect=AssertionError('不应联网')):
            self.assertEqual(self.invoke(cfg), 0)
        output = json.loads((self.base / 'work/config.json').read_text(encoding='utf-8'))
        self.assertEqual(output['width'], 1440)
        self.assertEqual((self.ep / 'voice.wav').read_bytes(), b'audio')

    def test_existing_work_survives(self):
        work = self.base / 'work'
        work.mkdir()
        sentinel = work / 'keep'
        sentinel.write_bytes(b'keep')
        with self.assertRaises(SystemExit):
            self.invoke({'beats': []})
        self.assertEqual(sentinel.read_bytes(), b'keep')

    def test_existing_output_survives(self):
        out = self.base / 'out'
        out.mkdir()
        with self.assertRaises(SystemExit):
            self.invoke({'beats': []}, '--render', '--output-dir', str(out))
        self.assertTrue(out.is_dir())
        self.assertFalse((self.base / 'work').exists())

    def test_default_no_network(self):
        with patch.object(build, 'run', side_effect=AssertionError('不应调用子进程')):
            with self.assertRaisesRegex(SystemExit, 'allow-tts-network'):
                build.make_voice('mock', self.base, 'd1', '台词', 'voice', '+8%', '+0%', 'norm', False)

    def test_cache_key_changes_with_text_voice_rate(self):
        paths = []
        def capture(cmd):
            paths.append(Path(cmd[-1]).name)
        with patch.object(build, 'run', side_effect=capture):
            import types
            async def save(_):
                pass
            fake = types.SimpleNamespace(Communicate=lambda *a, **kw: types.SimpleNamespace(save=save))
            with patch.dict(sys.modules, {'edge_tts': fake}):
                for text, voice, rate in [('甲', 'a', '+8%'), ('乙', 'a', '+8%'), ('甲', 'b', '+8%'), ('甲', 'a', '+0%')]:
                    build.make_voice('mock', self.base, 'd1', text, voice, rate, '+0%', 'norm', False, True)
        self.assertEqual(len(set(paths)), 4)

    def test_svg_existing_output_and_failed_process(self):
        out = self.base / 'test.png'
        out.write_bytes(b'old' * 1000)
        with patch.object(svg.subprocess, 'run') as run:
            with self.assertRaises(SystemExit):
                svg.render('mock', self.base / 'a.svg', out, 100, 100, 1)
            run.assert_not_called()
        self.assertEqual(out.read_bytes(), b'old' * 1000)
        with patch.object(svg.subprocess, 'run', return_value=type('Result', (), {'returncode': 1, 'stderr': '失败'})()):
            self.assertFalse(svg.render('mock', self.base / 'a.svg', self.base / 'new.png', 100, 100, 1))

    def test_record_rejects_existing_before_desktop_access(self):
        out = self.base / 'record.mp4'
        out.write_bytes(b'old-video')
        with patch.object(sys, 'argv', ['record', '--title', 'mock', '--out', str(out)]), patch.object(record, 'init_windows') as desktop, patch.object(record.subprocess, 'Popen') as process:
            with self.assertRaises(SystemExit):
                record.main()
            desktop.assert_not_called()
            process.assert_not_called()
        self.assertEqual(out.read_bytes(), b'old-video')

    def test_init_profile_custom_and_exists_guard(self):
        project = self.base / 'new-course'
        profile = self.base / 'profile.json'
        profile.write_text(json.dumps({'brand': '示例品牌', 'instructor': '讲师甲', 'fixed_open': '开始。', 'fixed_close': '再见。', 'font': 'sans-serif'}), encoding='utf-8')
        argv = ['init', '--root', str(project), '--size', '1440x1080', '--profile', str(profile)]
        with patch.object(sys, 'argv', argv):
            init.main()
        beats = project / 'episodes/EP01/beats.json'
        cfg = json.loads(beats.read_text(encoding='utf-8'))
        self.assertEqual(build.resolve_canvas(cfg['canvas']), (1440, 1080))
        self.assertEqual(cfg['beats'][-1]['text'], '再见。')
        beats.write_text('保留输入', encoding='utf-8')
        with patch.object(sys, 'argv', argv):
            init.main()
        self.assertEqual(beats.read_text(encoding='utf-8'), '保留输入')


if __name__ == '__main__':
    unittest.main()
