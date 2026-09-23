"""Current BluePrint application lifecycle; legacy product utilities retained."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen

DEFAULT_PORT = 8801


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if not args or args == ['--help'] or args == ['-h']:
        print('BluePrint operations interface\n\n  status --root WORKSPACE\n  serve --foreground --root WORKSPACE [--port PORT]\n  service start|restart|stop --root WORKSPACE\n  stage --source CHECKOUT --workspace WORKSPACE\n  activate --release RELEASE --workspace WORKSPACE\n  upgrade --root WORKSPACE [--quiet] [--dry-run]\n\nWorkspace utilities: doctor, found, seed-ops, hire. Use COMMAND --help for details.\nStarting the interface never hires agents or starts other engines.')
        return 0
    if args and args[0] in ('--version', '-V', 'version'):
        from protocolcity.distro import distro_version
        print(distro_version())
        return 0
    if args and args[0] == 'doctor':
        from .workspace_doctor import main as doctor
        return doctor(args[1:])
    if args and args[0] in ('stage','activate'):
        from .deploy import main as deploy
        original=sys.argv
        try: sys.argv=[original[0],*args]; return deploy() or 0
        finally: sys.argv=original
    if args and args[0]=='upgrade':
        args.pop(0)
        parser=argparse.ArgumentParser(prog='blueprint upgrade', description='Convert an existing three-lane install to the single consolidated app.')
        parser.add_argument('--root', required=True, type=Path)
        parser.add_argument('--quiet', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        options=parser.parse_args(args)
        from .deploy import upgrade
        try:
            result=upgrade(options.root, quiet=options.quiet, dry_run=options.dry_run)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr); return 1
        if options.quiet: print(json.dumps(result))
        return 0
    if args and args[0] in ('serve','status','service'):
        command=args.pop(0)
        service_action=args.pop(0) if command=='service' and args else 'status'
        parser=argparse.ArgumentParser(prog='blueprint '+command)
        parser.add_argument('--root','--binder',dest='root',type=Path,default=Path.cwd())
        parser.add_argument('--port',type=int,default=DEFAULT_PORT)
        parser.add_argument('--foreground',action='store_true')
        options=parser.parse_args(args)
        root=options.root.expanduser().resolve()
        receipt_path=root/'.blueprint/deployment.json'
        try: receipt=json.loads(receipt_path.read_text())
        except (OSError,ValueError): receipt={}
        if command=='serve' and options.foreground:
            from .desk_entry import overview
            sys.argv=['blueprint-overview','--binder',str(root),'--port',str(options.port)]
            return overview() or 0
        label='gui/'+str(os.getuid())+'/com.protocolcity.blueprint-overview'
        if command=='service' and service_action!='status':
            if service_action not in ('start','restart','stop'):
                parser.error('Service action must be status, start, restart, or stop.')
            agent=Path(receipt.get('launch_agent') or Path.home()/'Library/LaunchAgents/com.protocolcity.blueprint-overview.plist')
            if not agent.is_file():parser.error('No installed BluePrint service. Stage and activate a release first.')
            if service_action=='stop': action=['launchctl','bootout',label]
            elif service_action=='restart': action=['launchctl','kickstart','-k',label]
            else:
                loaded=subprocess.run(['launchctl','print',label],capture_output=True,timeout=10).returncode==0
                action=['launchctl','kickstart',label] if loaded else ['launchctl','bootstrap','gui/'+str(os.getuid()),str(agent)]
            try: subprocess.run(action,check=True,timeout=30)
            except (subprocess.SubprocessError,OSError) as exc: print('Service action failed: '+str(exc),file=sys.stderr);return 1
            if service_action=='stop':print('BluePrint stopped. WorkLane and WorkForce were not stopped.');return 0
        port=receipt.get('port',options.port)
        try:
            with urlopen(f'http://127.0.0.1:{port}/api/operations',timeout=5) as response: actual=json.load(response)
            print(json.dumps({'url':f'http://127.0.0.1:{port}/','build':actual.get('build'),'workspace':actual.get('workspace'),'deployment':receipt or None},indent=2))
            return 0
        except (OSError,ValueError):
            print('BluePrint is not responding. Use blueprint service start --root <workspace>, or blueprint serve --foreground --root <workspace>.',file=sys.stderr);return 1
    if args and args[0] in ('update','install','uninstall'):
        print('Upgrading an existing install (brew or pip)? Run: blueprint upgrade --root <workspace>. Building from a source checkout instead? Use blueprint stage --source <checkout> --workspace <workspace>, then blueprint activate --release <release> --workspace <workspace>. Engine and package changes are separate.',file=sys.stderr)
        return 2
    from .cli import main as legacy
    return legacy(args)
