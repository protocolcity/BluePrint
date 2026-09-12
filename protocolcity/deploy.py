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
import subprocess
import sys
import tempfile
import time
import urllib.request
import venv
import zipfile

LABEL = 'com.protocolcity.blueprint-overview'


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


def probe(port, expected, attempts=30, workspace=None):
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/operations', timeout=2) as response:
                value = json.load(response)
            if value.get('build') == expected and value.get('workspace') and (workspace is None or value['workspace'].get('path') == str(workspace)):
                return value
        except (OSError, ValueError):
            pass
        time.sleep(.3)
    raise RuntimeError(f'BluePrint on port {port} did not report build {expected}.')


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


def register_agent(domain, agent, label):
    for attempt in range(8):
        result=subprocess.run(['launchctl','bootstrap',domain,str(agent)],capture_output=True,text=True,timeout=15)
        if result.returncode==0: return
        if subprocess.run(['launchctl','print',domain+'/'+label],capture_output=True,timeout=5).returncode==0: return
        time.sleep(.5)
    raise RuntimeError('Service registration did not settle: '+result.stderr.strip())


def activate(release, workspace, port, legacy_ports=None):
    current=workspace/'local/blueprint/current'
    if current.exists() and not current.is_symlink():
        raise RuntimeError('Current release path is not a symlink; inspect before activation.')
    receipt = json.loads((release/'build.json').read_text())
    executable = Path(receipt['entrypoint'])
    if not executable.is_file() or not executable.resolve().is_relative_to(release):
        raise RuntimeError('Invalid release entrypoint.')
    # Verify the installed package before touching launchd. Port 0 asks the OS
    # to allocate a port; the readiness check below uses an independently bound
    # candidate port from a short-lived socket, with a startup failure detected.
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); candidate_port = sock.getsockname()[1]
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen([str(executable),'--binder',str(workspace),'--port',str(candidate_port)], stdout=log, stderr=log)
        try:
            probe(candidate_port, receipt['version'], workspace=workspace)
        finally:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
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
    if previous:
        (release/'previous-launch-agent.plist').write_bytes(previous)
    if previous_receipt.exists():
        (release/'previous-deployment.json').write_bytes(previous_receipt.read_bytes())
    agent.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(['launchctl','bootout',domain+'/'+LABEL], capture_output=True, timeout=30)
        agent.write_bytes(plistlib.dumps(config))
        register_agent(domain,agent,LABEL)
        snapshot = probe(port, receipt['version'], workspace=workspace)
    except Exception:
        subprocess.run(['launchctl','bootout',domain+'/'+LABEL], capture_output=True, timeout=30)
        if previous:
            agent.write_bytes(previous)
            register_agent(domain,agent,LABEL)
        else:
            agent.unlink(missing_ok=True)
        raise
    write_json(previous_receipt, {**receipt, 'port':port, 'launch_agent':str(agent), 'active':True,
        'activated_at':datetime.now(timezone.utc).isoformat()})
    current=workspace/'local/blueprint/current'
    if current.exists() and not current.is_symlink():
        raise RuntimeError('App activated, but current release path is not a symlink; inspect it before changing commands.')
    pending=current.with_name('current.pending')
    pending.unlink(missing_ok=True)
    pending.symlink_to(release, target_is_directory=True)
    pending.replace(current)
    print(json.dumps({'active':receipt['version'], 'url':f'http://127.0.0.1:{port}', 'projects':len(snapshot['projects'])}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage','activate'])
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--port', type=int, default=8803)
    parser.add_argument('--legacy-port', action='append', type=int)
    args=parser.parse_args()
    workspace=args.workspace.expanduser().resolve()
    if not workspace.is_dir(): parser.error('Workspace must already exist.')
    if args.action=='stage':
        if not args.source: parser.error('--source is required to identify the checkout being built.')
        stage(args.source.expanduser().resolve(),workspace,args.python)
    else:
        if not args.release: parser.error('--release is required for activation or rollback.')
        activate(args.release.expanduser().resolve(),workspace,args.port,args.legacy_port)

if __name__=='__main__': main()
