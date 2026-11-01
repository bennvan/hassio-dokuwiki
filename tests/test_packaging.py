import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sources', ROOT / 'dokuwiki/tools/sources.py')
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


class PackagingTests(unittest.TestCase):
    def test_initialization_never_replaces_user_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / 'seed'
            (seed / 'conf').mkdir(parents=True)
            (seed / 'data/pages').mkdir(parents=True)
            (seed / 'conf/setting.txt').write_text('starter')
            storage = root / 'wiki'
            cmd = ['php', str(ROOT / 'dokuwiki/runtime/init-storage.php'), str(storage), str(seed)]
            subprocess.run(cmd, check=True, capture_output=True)
            (storage / 'conf/setting.txt').write_text('user choice')
            (storage / 'data/pages/private.txt').write_text('user content')
            (seed / 'conf/setting.txt').write_text('changed release defaults')
            subprocess.run(cmd, check=True, capture_output=True)
            self.assertEqual((storage / 'conf/setting.txt').read_text(), 'user choice')
            self.assertEqual((storage / 'data/pages/private.txt').read_text(), 'user content')

    def test_unknown_existing_data_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = root / 'wiki'
            storage.mkdir()
            sentinel = storage / 'existing.txt'
            sentinel.write_text('keep')
            result = subprocess.run(['php', str(ROOT / 'dokuwiki/runtime/init-storage.php'),
                                     str(storage), str(root / 'missing-seed')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'keep')

    def test_source_filter_rejects_external_links_and_runtime_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / 'plugin'
            plugin.mkdir()
            outside = root / 'secret.txt'
            outside.write_text('private')
            link = plugin / 'external.txt'
            link.symlink_to(outside)
            with self.assertRaises(ValueError):
                sources.tree_hash(plugin)
            link.unlink()
            (plugin / 'database.sqlite3').write_text('private')
            with self.assertRaises(ValueError):
                sources.tree_hash(plugin)

    def test_internal_help_links_and_git_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'help.txt').write_text('help')
            (root / 'alias.txt').symlink_to('help.txt')
            before = sources.tree_hash(root)
            (root / '.git').mkdir()
            (root / '.git/config').write_text('not packaged')
            self.assertEqual(sources.tree_hash(root), before)

    def test_preview_cannot_write_into_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                sources.prepare(root, root / 'not-read.tgz', root / 'nested-output')


if __name__ == '__main__':
    unittest.main()
