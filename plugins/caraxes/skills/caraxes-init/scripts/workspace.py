"""Initialize and locate Caraxes data without writing to target repositories."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

DIRECTORIES = ('principles', 'stacks', 'projects', 'work')


class WorkspaceError(ValueError):
    """A workspace cannot be used without user intervention."""


def absolute_path(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise WorkspaceError('Use an absolute workspace path.')
    return path.resolve()


def repository_root(path):
    for parent in (path, *path.parents):
        if (parent / '.git').exists():
            return parent
    return None


def check_outside_project(path, project):
    if path.is_relative_to(project) or repository_root(path) is not None:
        raise WorkspaceError(f'Caraxes data must be outside project repositories: {path}')


def read_config(config):
    if config.is_symlink():
        raise WorkspaceError(f'Configuration must not be a symbolic link: {config}')
    if not config.exists():
        return None
    try:
        data = json.loads(config.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise WorkspaceError(f'Invalid configuration; preserve and repair {config}') from exc
    if (not isinstance(data, dict)
            or type(data.get('schema_version')) is not int
            or data['schema_version'] != 1
            or not isinstance(data.get('workspace_path'), str)
            or not data['workspace_path']):
        raise WorkspaceError(f'Unsupported configuration; preserve and repair {config}')
    return absolute_path(data['workspace_path'])


def check_workspace(path, config_dir, home, project):
    check_outside_project(path, project)
    if (path == home or path == Path(path.anchor)
            or config_dir.is_relative_to(path) or project.is_relative_to(path)):
        raise WorkspaceError('Choose a dedicated workspace directory outside the project.')
    if path.exists() and not path.is_dir():
        raise WorkspaceError(f'Workspace path is not a directory: {path}')
    for name in DIRECTORIES:
        child = path / name
        if child.is_symlink() or (child.exists() and not child.is_dir()):
            raise WorkspaceError(f'Expected an ordinary directory; preserve and repair {child}')


def publish_config(config, path):
    """Publish complete JSON under an exclusive initialization lock."""
    lock = config.parent / '.init.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise WorkspaceError(f'Initialization is locked. Check for another run: {lock}') from exc
    os.close(fd)
    temporary = None
    try:
        existing = read_config(config)
        if existing is not None:
            if existing != path:
                raise WorkspaceError('Another initialization registered a different workspace.')
            return
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=config.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump({'schema_version': 1, 'workspace_path': str(path)}, output, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, config)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        lock.unlink()


def run(operation, project, target=None, *, home=None):
    """Resolve afresh on every call; home injection is for isolated tests only."""
    if operation not in ('init', 'resolve'):
        raise WorkspaceError('Unknown operation.')
    if operation == 'resolve' and target is not None:
        raise WorkspaceError('A custom path is only accepted by init.')
    home = (Path.home() if home is None else Path(home)).resolve()
    project = absolute_path(project)
    if not project.is_dir():
        raise WorkspaceError('The project directory must exist.')
    project = repository_root(project) or project
    config_dir = (home / '.caraxes').resolve()
    check_outside_project(config_dir, project)
    config = config_dir / 'config.json'
    requested = absolute_path(target) if target is not None else None
    registered = read_config(config)
    if registered is not None:
        if requested is not None and requested != registered:
            raise WorkspaceError('A different workspace is already registered; automatic switching is not supported.')
        path = registered
        if not path.is_dir():
            raise WorkspaceError(f'Registered workspace is missing or unavailable: {path}. Restore it before continuing.')
    else:
        if operation == 'resolve':
            raise WorkspaceError('No workspace is registered. Run caraxes-init first.')
        path = requested if requested is not None else config_dir / 'workspace'
        path = path.resolve()
    check_workspace(path, config_dir, home, project)
    created = []
    if operation == 'init':
        config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        for name in DIRECTORIES:
            child = path / name
            if not child.exists():
                child.mkdir(mode=0o700)
                created.append(name)
        if registered is None:
            publish_config(config, path)
    missing = [name for name in DIRECTORIES if not (path / name).is_dir()]
    return {'status': 'incomplete' if missing else 'ready',
            'workspace_path': str(path), 'config_path': str(config),
            'created_directories': created, 'missing_directories': missing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    for name in ('init', 'resolve'):
        command = commands.add_parser(name)
        command.add_argument('--project', required=True,
                             help='Absolute target project directory; nested Git paths resolve to their root.')
        if name == 'init':
            command.add_argument('--workspace', help='Absolute custom path for first initialization.')
    args = parser.parse_args()
    try:
        result = run(args.operation, args.project, getattr(args, 'workspace', None))
    except (WorkspaceError, OSError, RuntimeError) as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
