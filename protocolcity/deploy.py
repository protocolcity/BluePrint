#!/usr/bin/env python3
"""Build and activate an isolated BluePrint release on macOS.

No git checkout/pull, engine restart, or runtime-data migration is performed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import venv
import zipfile

LABEL = 'com.protocolcity.blueprint-overview'
DEFAULT_PORT = 8801
# Leftover split ports from the three-lane install (old Map / old Overview).
DEFAULT_LEGACY_PORTS = (8802, 8803)
DEFAULT_PROBE_TIMEOUT = 60.0
DEFAULT_PROBE_INTERVAL = 0.3


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, text=True, timeout=180, **kwargs)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def metadata(wheel):
    with zipfile.ZipFile(wheel) as archive:
        entry = next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
        values = archive.read(entry).decode().splitlines()
    return next(line[9:] for line in values if line.startswith('Version: '))


def probe(port, expected, workspace=None, timeout=DEFAULT_PROBE_TIMEOUT, interval=DEFAULT_PROBE_INTERVAL):
    """Poll /api/operations until the expected build is live or the budget expires."""
    deadline = time.monotonic() + float(timeout)
    last_build = None
    saw_response = False
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/operations', timeout=2) as response:
                value = json.load(response)
            saw_response = True
            build = value.get('build')
            workspace_ok = value.get('workspace') and (
                workspace is None or value['workspace'].get('path') == str(workspace)
            )
            if build == expected and workspace_ok:
                return value
            if build is not None:
                last_build = build
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        time.sleep(interval)
    if saw_response and last_build is not None and last_build != expected:
        raise RuntimeError(
            f'BluePrint on port {port} reported build {last_build}, expected {expected}.'
        )
    if saw_response:
        raise RuntimeError(f'BluePrint on port {port} did not report build {expected}.')
    raise RuntimeError(f'BluePrint on port {port} did not respond within {timeout:g}s.')


def stage(source, workspace, python):
    releases = workspace / 'local/blueprint/releases'
    releases.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bp-build-') as temporary:
        run([python, '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir', temporary, source])
        wheel = next(Path(temporary).glob('protocolcity_blueprint-*.whl'))
        version = metadata(wheel)
        release = releases / version
        if release.exists():
            raise RuntimeError('This release already exists. Bump the package version; releases are immutable.')
        release.mkdir()
        destination = release / wheel.name
        destination.write_bytes(wheel.read_bytes())
        run([python, '-m', 'venv', release / 'venv'])
        run([release/'venv/bin/python', '-m', 'pip', 'install', '--no-deps', destination])
    head = run(['git', '-C', source, 'rev-parse', 'HEAD'], capture_output=True).stdout.strip()
    dirty = run(['git', '-C', source, 'status', '--porcelain'], capture_output=True).stdout.strip()
    remote = run(['git', '-C', source, 'remote', 'get-url', 'origin'], capture_output=True).stdout.strip()
    receipt = dict(version=version, source=str(source), repository=remote, source_head=head,
                   uncommitted_changes=bool(dirty), wheel_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                   entrypoint=str(release/'venv/bin/blueprint-overview'), built_at=datetime.now(timezone.utc).isoformat())
    write_json(release/'build.json', receipt)
    print(json.dumps({'staged':str(release), 'version':version}))
    return release


_BOOTSTRAP_UNCERTAIN = (
    'input/output error',
    'i/o error',
    'io error',
    'resource temporarily unavailable',
)


def bootstrap_may_have_started(result):
    """True when launchctl bootstrap failed in a way that may still have started the job.

    An I/O miss (pc-1554) can leave a wedged overview process listening while
    activate believes registration failed. Callers must bootout before retry.
    """
    if getattr(result, 'returncode', 1) == 0:
        return False
    text = f"{getattr(result, 'stderr', '') or ''} {getattr(result, 'stdout', '') or ''}".lower()
    if not text.strip():
        return True
    return any(marker in text for marker in _BOOTSTRAP_UNCERTAIN)


def stop_process(process, timeout=5):
    """Terminate a preflight overview process; escalate to kill / process-group.

    Activate must not leave a candidate listener after probe failure or a
    bootstrap I/O miss (pc-1554).
    """
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    except OSError:
        pass
    try:
        process.kill()
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        pid = getattr(process, 'pid', None)
        if pid:
            try:
                os.killpg(pid, 9)
            except OSError:
                pass
            try:
                process.wait(timeout=2)
            except (subprocess.TimeoutExpired, OSError):
                pass
    except OSError:
        pass


def register_agent(domain, agent, label):
    result = None
    for attempt in range(8):
        result=subprocess.run(['launchctl','bootstrap',domain,str(agent)],capture_output=True,text=True,timeout=15)
        if result.returncode==0: return
        if subprocess.run(['launchctl','print',domain+'/'+label],capture_output=True,timeout=5).returncode==0: return
        # I/O miss: the job may already be running. Boot it out before the
        # next bootstrap so activate cannot stack a wedged listener (pc-1554).
        if bootstrap_may_have_started(result):
            subprocess.run(['launchctl','bootout',domain+'/'+label], capture_output=True, timeout=30)
        time.sleep(.5)
    raise RuntimeError('Service registration did not settle: '+(result.stderr.strip() if result else ''))


def deployment_matches(agent_path, deployment_path, executable, version, port, legacy_ports):
    """True when the launch agent and deployment receipt already match *version*."""
    if not agent_path.is_file() or not deployment_path.is_file():
        return False
    try:
        existing = json.loads(deployment_path.read_text())
        config = plistlib.loads(agent_path.read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException):
        return False
    args = config.get('ProgramArguments', [])
    existing_legacy = [int(args[i+1]) for i,value in enumerate(args[:-1]) if value=='--legacy-port']
    return (existing.get('version')==version and existing.get('port')==port
            and existing.get('entrypoint')==str(executable) and existing_legacy==list(legacy_ports))


def activate_agent(executable, receipt, workspace, port, legacy_ports=None, backup_dir=None, probe_timeout=DEFAULT_PROBE_TIMEOUT):
    """Write and bootstrap the single blueprint-overview launch agent.

    Shared by ``activate`` (source-built release) and ``upgrade`` (installed
    package entrypoint); the launch-agent shape and the deployment receipt are
    identical either way.
    """
    executable = Path(executable)
    if not executable.is_file():
        raise RuntimeError('Invalid entrypoint: '+str(executable))
    # Verify the installed package before touching launchd. Port 0 asks the OS
    # to allocate a port; the readiness check below uses an independently bound
    # candidate port from a short-lived socket, with a startup failure detected.
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); candidate_port = sock.getsockname()[1]
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [str(executable),'--binder',str(workspace),'--port',str(candidate_port)],
            stdout=log, stderr=log, start_new_session=True)
        try:
            probe(candidate_port, receipt['version'], workspace=workspace, timeout=min(probe_timeout, 30))
        finally:
            stop_process(process, timeout=5)
    agent = Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'
    previous = agent.read_bytes() if agent.exists() else None
    config = plistlib.loads(previous) if previous else {'Label':LABEL,'RunAtLoad':True,'KeepAlive':True}
    prior_args=config.get('ProgramArguments', [])
    if legacy_ports is None:
        legacy_ports=[int(prior_args[i+1]) for i,value in enumerate(prior_args[:-1]) if value=='--legacy-port']
    arguments=[str(executable),'--binder',str(workspace),'--port',str(port)]
    for legacy_port in legacy_ports: arguments.extend(['--legacy-port',str(legacy_port)])
    config.update(ProgramArguments=arguments, WorkingDirectory=str(workspace))
    config.setdefault('EnvironmentVariables', {}).update(PATH='/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1')
    domain = f'gui/{os.getuid()}'
    previous_receipt = workspace/'.blueprint/deployment.json'
    if backup_dir is not None:
        if previous:
            (backup_dir/'previous-launch-agent.plist').write_bytes(previous)
        if previous_receipt.exists():
            (backup_dir/'previous-deployment.json').write_bytes(previous_receipt.read_bytes())
    agent.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(['launchctl','bootout',domain+'/'+LABEL], capture_output=True, timeout=30)
        agent.write_bytes(plistlib.dumps(config))
        register_agent(domain,agent,LABEL)
        snapshot = probe(port, receipt['version'], workspace=workspace, timeout=probe_timeout)
    except Exception:
        # Bootstrap I/O miss can leave the new job running. Boot out twice
        # so a wedged listener does not survive the rollback (pc-1554).
        subprocess.run(['launchctl','bootout',domain+'/'+LABEL], capture_output=True, timeout=30)
        time.sleep(0.2)
        subprocess.run(['launchctl','bootout',domain+'/'+LABEL], capture_output=True, timeout=30)
        if previous:
            agent.write_bytes(previous)
            register_agent(domain,agent,LABEL)
        else:
            agent.unlink(missing_ok=True)
        raise
    write_json(previous_receipt, {**receipt, 'port':port, 'launch_agent':str(agent), 'active':True,
        'activated_at':datetime.now(timezone.utc).isoformat()})
    return snapshot


def activate(release, workspace, port, legacy_ports=None, probe_timeout=DEFAULT_PROBE_TIMEOUT):
    current=workspace/'local/blueprint/current'
    if current.exists() and not current.is_symlink():
        raise RuntimeError('Current release path is not a symlink; inspect before activation.')
    receipt = json.loads((release/'build.json').read_text())
    executable = Path(receipt['entrypoint'])
    if not executable.is_file() or not executable.resolve().is_relative_to(release):
        raise RuntimeError('Invalid release entrypoint.')
    agent_path = Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'
    deployment_path = workspace/'.blueprint/deployment.json'
    resolved_legacy = list(legacy_ports) if legacy_ports is not None else None
    if resolved_legacy is None and agent_path.is_file():
        prior_args = plistlib.loads(agent_path.read_bytes()).get('ProgramArguments', [])
        resolved_legacy = [int(prior_args[i+1]) for i,value in enumerate(prior_args[:-1]) if value=='--legacy-port']
    if resolved_legacy is None:
        resolved_legacy = []
    if (current.is_symlink() and current.resolve() == release.resolve()
            and deployment_matches(agent_path, deployment_path, executable, receipt['version'], port, resolved_legacy)):
        try:
            snapshot = probe(port, receipt['version'], workspace=workspace, timeout=probe_timeout)
            print('Release '+receipt['version']+' is already active at http://127.0.0.1:'+str(port)+'.')
            print(json.dumps({'active':receipt['version'], 'url':f'http://127.0.0.1:{port}',
                              'projects':len(snapshot['projects']), 'no_op':True}))
            return
        except RuntimeError:
            pass
    snapshot = activate_agent(executable, receipt, workspace, port, resolved_legacy, backup_dir=release,
                              probe_timeout=probe_timeout)
    current=workspace/'local/blueprint/current'
    if current.exists() and not current.is_symlink():
        raise RuntimeError('App activated, but current release path is not a symlink; inspect it before changing commands.')
    pending=current.with_name('current.pending')
    pending.unlink(missing_ok=True)
    pending.symlink_to(release, target_is_directory=True)
    pending.replace(current)
    print(json.dumps({'active':receipt['version'], 'url':f'http://127.0.0.1:{port}', 'projects':len(snapshot['projects'])}))


def resolve_installed_executable(python=None):
    """Locate the packaged ``blueprint-overview`` entrypoint (brew or venv install)."""
    python = Path(python) if python else Path(sys.executable)
    candidate = python.parent/'blueprint-overview'
    if candidate.is_file():
        return candidate
    found = shutil.which('blueprint-overview')
    if found:
        return Path(found)
    raise RuntimeError('blueprint-overview entrypoint not found next to '+str(python)+' or on PATH.')


def installed_version():
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version('protocolcity-blueprint')
    except PackageNotFoundError as exc:
        raise RuntimeError('Could not determine the installed BluePrint version: '+str(exc)) from exc


def url_map(port, legacy_ports):
    lines = [f'http://127.0.0.1:{legacy_port}/  ->  http://127.0.0.1:{port}/  (307 redirect)' for legacy_port in legacy_ports]
    aliases = {'/desk':'/work', '/roster':'/agents', '/workspace-map':'/map', '/overview':'/'}
    lines += [f'http://127.0.0.1:{port}{old}  ->  http://127.0.0.1:{port}{new}' for old, new in aliases.items()]
    return lines


def _looks_like_workspace(workspace):
    """True when ``workspace`` has a BluePrint marker to write against.

    Refuses arbitrary directories: requires ``.blueprint/``, ``.protocolcity/``,
    or at least one project's ``.protocolcity/desk-join.json``.
    """
    if (workspace/'.blueprint').is_dir() or (workspace/'.protocolcity').is_dir():
        return True
    return any(workspace.glob('*/.protocolcity/desk-join.json'))


def upgrade(workspace, *, port=DEFAULT_PORT, legacy_ports=DEFAULT_LEGACY_PORTS, python=None, quiet=False, dry_run=False):
    """Convert an existing three-lane install to the single consolidated app.

    Boots out and retires the legacy launch agents, then writes the single
    blueprint-overview agent for the *installed* package (no build/stage
    step). Idempotent: a second run with nothing to change is a no-op.
    """
    from . import service as service_mod
    workspace = Path(workspace).expanduser().resolve()
    if not workspace.is_dir():
        raise RuntimeError('Workspace must already exist.')
    if not service_mod.is_macos():
        raise RuntimeError('blueprint upgrade manages launchd agents and is macOS-only today.')
    if not _looks_like_workspace(workspace):
        raise RuntimeError(
            f"'{workspace}' does not look like a BluePrint workspace (expected "
            ".blueprint/, .protocolcity/, or a project's .protocolcity/desk-join.json)."
        )
    legacy_ports = list(legacy_ports)
    legacy = service_mod.retire_legacy_agents(workspace=workspace, quiet=quiet, dry_run=dry_run)
    executable = resolve_installed_executable(python)
    version = installed_version()
    agent_path = Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'
    deployment_path = workspace/'.blueprint/deployment.json'
    already_current = deployment_matches(agent_path, deployment_path, executable, version, port, legacy_ports)
    plan = {'workspace':str(workspace), 'legacy_agents':legacy, 'entrypoint':str(executable),
            'version':version, 'port':port, 'legacy_ports':legacy_ports, 'already_current':already_current}
    if dry_run:
        plan['action']='dry-run'
        if not quiet:
            print(json.dumps(plan, indent=2))
        return plan
    if already_current:
        plan['action']='no-op'
        if not quiet:
            print('BluePrint agent already reflects the installed build; nothing to do.')
            print('\n'.join(url_map(port, legacy_ports)))
        return plan
    receipt = {'version':version, 'source':'installed-package', 'entrypoint':str(executable),
               'built_at':datetime.now(timezone.utc).isoformat()}
    backup_dir = workspace/'local/blueprint/retired-services'/datetime.now(timezone.utc).strftime('%Y-%m-%d')/'upgrade-backup'
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        activate_agent(executable, receipt, workspace, port, legacy_ports, backup_dir=backup_dir)
    except Exception:
        # activate_agent already restores the previous launch agent plist from
        # memory on failure; restore the deployment receipt from the snapshot
        # taken just above so :8801's on-disk record does not point at a build
        # that never went live.
        backup_receipt = backup_dir/'previous-deployment.json'
        if backup_receipt.is_file():
            deployment_path.write_bytes(backup_receipt.read_bytes())
        raise
    plan['action']='activated'
    if not quiet:
        print(json.dumps({'active':version, 'url':f'http://127.0.0.1:{port}'}))
        print('\n'.join(url_map(port, legacy_ports)))
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage','activate'])
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--legacy-port', action='append', type=int)
    parser.add_argument('--probe-timeout', type=float, default=DEFAULT_PROBE_TIMEOUT,
                        help='Seconds to wait for the service to report the expected build after restart.')
    args=parser.parse_args()
    workspace=args.workspace.expanduser().resolve()
    if not workspace.is_dir(): parser.error('Workspace must already exist.')
    if args.action=='stage':
        if not args.source: parser.error('--source is required to identify the checkout being built.')
        stage(args.source.expanduser().resolve(),workspace,args.python)
    else:
        if not args.release: parser.error('--release is required for activation or rollback.')
        activate(args.release.expanduser().resolve(),workspace,args.port,args.legacy_port,
                 probe_timeout=args.probe_timeout)

if __name__=='__main__': main()
