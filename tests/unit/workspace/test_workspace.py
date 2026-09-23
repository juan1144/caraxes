import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[3] / 'plugins/caraxes/skills/caraxes-init/scripts/workspace.py'
spec = importlib.util.spec_from_file_location('workspace', SCRIPT)
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / 'user home'
        self.home.mkdir()
        self.project = self.root / 'project'
        self.project.mkdir()
        (self.project / '.git').mkdir()
        self.config = self.home / '.caraxes/config.json'
        self.default = self.home / '.caraxes/workspace'

    def run_operation(self, operation='init', target=None, project=None):
        return workspace.run(operation, project or self.project, target, home=self.home)

    def test_default_structure_and_pointer(self):
        result = self.run_operation()
        self.assertEqual(result['workspace_path'], str(self.default))
        self.assertEqual({p.name for p in self.default.iterdir()}, set(workspace.DIRECTORIES))
        self.assertEqual(json.loads(self.config.read_text()), {
            'schema_version': 1, 'workspace_path': str(self.default)})
        self.assertEqual(list(self.project.iterdir()), [self.project / '.git'])

    def test_custom_path_resolves_from_saved_configuration(self):
        target = self.root / 'custom workspace'
        self.run_operation(target=target)
        with patch.object(workspace.Path, 'home', return_value=self.home):
            result = workspace.run('resolve', self.project)
        self.assertEqual(result['workspace_path'], str(target))
        self.assertFalse(self.default.exists())

    def test_repeat_preserves_content_and_config(self):
        self.run_operation()
        note = self.default / 'principles/example.md'
        note.write_text('User content')
        before = self.config.read_bytes()
        self.run_operation()
        self.assertEqual(note.read_text(), 'User content')
        self.assertEqual(self.config.read_bytes(), before)

    def test_init_repairs_missing_child_but_resolve_does_not(self):
        self.run_operation()
        (self.default / 'stacks').rmdir()
        self.assertEqual(self.run_operation('resolve')['missing_directories'], ['stacks'])
        self.assertFalse((self.default / 'stacks').exists())
        self.run_operation()
        self.assertTrue((self.default / 'stacks').is_dir())

    def test_resolve_unconfigured_is_read_only(self):
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation('resolve')
        self.assertFalse(self.config.parent.exists())

    def test_missing_registered_workspace_is_not_recreated(self):
        self.run_operation()
        for child in self.default.iterdir():
            child.rmdir()
        self.default.rmdir()
        for operation in ('init', 'resolve'):
            with self.assertRaises(workspace.WorkspaceError):
                self.run_operation(operation)
        self.assertFalse(self.default.exists())

    def test_refuses_switch(self):
        self.run_operation()
        target = self.root / 'other'
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation(target=target)
        self.assertFalse(target.exists())

    def test_corrupt_config_is_preserved(self):
        self.config.parent.mkdir()
        for content in ('{', '[]', '{"schema_version": 2}',
                        '{"schema_version": 1, "workspace_path": "relative"}',
                        '{"schema_version": true, "workspace_path": "/tmp"}'):
            self.config.write_text(content)
            with self.subTest(content=content), self.assertRaises(workspace.WorkspaceError):
                self.run_operation()
            self.assertEqual(self.config.read_text(), content)
        self.assertFalse(self.default.exists())

    def test_refuses_project_and_nested_repo_paths(self):
        nested = self.project / 'src'
        nested.mkdir()
        for target in (self.project, self.project / 'specs', nested / 'specs'):
            with self.subTest(target=target), self.assertRaises(workspace.WorkspaceError):
                self.run_operation(target=target, project=nested)
        self.assertFalse(self.config.exists())

    def test_refuses_other_repository(self):
        other = self.root / 'other-repo'
        other.mkdir()
        (other / '.git').write_text('gitdir: elsewhere')
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation(target=other / 'specs')

    def test_file_conflict_preflight(self):
        self.default.mkdir(parents=True)
        conflict = self.default / 'work'
        conflict.write_text('keep')
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation()
        self.assertEqual(list(self.default.iterdir()), [conflict])
        self.assertFalse(self.config.exists())

    def test_relative_path_rejected(self):
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation(target=Path('relative'))
        self.assertFalse(self.config.exists())

    def test_home_and_config_directory_rejected(self):
        for target in (self.home, self.home / '.caraxes', self.root):
            with self.subTest(target=target), self.assertRaises(workspace.WorkspaceError):
                self.run_operation(target=target)

    def test_config_inside_project_rejected(self):
        (self.home / '.git').mkdir()
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation(target=self.root / 'outside')
        self.assertFalse(self.config.exists())

    def symlink(self, link, destination):
        try:
            link.symlink_to(destination, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f'Symlinks unavailable: {exc}')

    def test_symlink_into_project_rejected(self):
        alias = self.root / 'alias'
        self.symlink(alias, self.project)
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation(target=alias / 'specs')
        self.assertFalse((self.project / 'specs').exists())

    def test_child_symlink_rejected(self):
        self.default.mkdir(parents=True)
        self.symlink(self.default / 'work', self.project)
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation()
        self.assertFalse(self.config.exists())

    def test_permission_failure_does_not_register(self):
        with patch.object(workspace.Path, 'mkdir', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                self.run_operation()
        self.assertFalse(self.config.exists())

    def test_failed_config_publish_leaves_no_partial_config(self):
        with patch.object(workspace.os, 'replace', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                self.run_operation()
        self.assertFalse(self.config.exists())
        self.assertFalse((self.config.parent / '.init.lock').exists())
        self.assertEqual(list(self.config.parent.iterdir()), [self.default])
        self.run_operation()
        self.assertTrue(self.config.exists())

    def test_existing_lock_is_preserved(self):
        self.config.parent.mkdir()
        lock = self.config.parent / '.init.lock'
        lock.write_text('another run')
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation()
        self.assertEqual(lock.read_text(), 'another run')
        self.assertFalse(self.config.exists())

    def test_config_symlink_is_rejected(self):
        self.config.parent.mkdir()
        destination = self.root / 'other-config.json'
        destination.write_text('{}')
        try:
            self.config.symlink_to(destination)
        except OSError as exc:
            self.skipTest(f'Symlinks unavailable: {exc}')
        with self.assertRaises(workspace.WorkspaceError):
            self.run_operation()
        self.assertEqual(destination.read_text(), '{}')

    def test_cli_errors_are_json(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'init', '--project',
                                 str(self.project), '--workspace', 'relative'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)['status'], 'error')
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
