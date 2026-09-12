"""An allowlisted local paper catalog; never a general filesystem endpoint."""
from pathlib import Path
from .operations import project_registry

ROOT_PAPERS = ('README.md','MARKETING.md','PRODUCT.md','ARCHITECTURE.md','AGENTS.md','BOUNDARIES.md','INSTALL.md','RUNNING.md','PROCESS.md','CONSOLIDATION.md','ENTRY.md')


def layer(path):
    name=path.name.upper()
    if name in ('README.MD','MARKETING.MD','PRODUCT.MD'): return 'Product'
    if name in ('INSTALL.MD','RUNNING.MD','PROCESS.MD','ENTRY.MD') or any(part in ('ops','operations') for part in path.parts): return 'Operations'
    if name in ('ARCHITECTURE.MD','BOUNDARIES.MD') or any(part in ('specs','decisions','architecture') for part in path.parts): return 'System'
    return 'Development'


def catalog(binder, project):
    if not binder: raise ValueError('No workspace selected.')
    root=Path(binder).resolve()
    registry=project_registry(root)
    if project not in registry: raise ValueError('Select a registered project.')
    folder=root/registry[project]['folder']
    candidates=[folder/name for name in ROOT_PAPERS]
    docs=folder/'docs'
    if docs.is_dir() and docs.resolve().is_relative_to(folder.resolve()):
        candidates.extend(sorted(docs.rglob('*.md')))
    papers=[]
    for path in candidates:
        if not path.is_file() or not path.resolve().is_relative_to(folder.resolve()): continue
        relative=path.relative_to(folder)
        if any(part.startswith('.') or part.lower() in ('local','secrets','credentials','customers') for part in relative.parts): continue
        papers.append({'path':str(relative), 'title':path.stem.replace('_',' ').replace('-',' '),
                       'layer':layer(relative), 'bytes':path.stat().st_size, 'exposure':'Local source · publication not assessed'})
    return {'project':project, 'name':registry[project]['name'], 'papers':papers[:500], 'truncated':len(papers)>500}


def read_document(binder, project, name):
    listing=catalog(binder, project)
    paper=next((p for p in listing['papers'] if p['path']==name),None)
    if not paper: raise FileNotFoundError('Document is not in this project catalog.')
    root=Path(binder).resolve()
    folder=root/project_registry(root)[project]['folder']
    path=(folder/name).resolve()
    if not path.is_relative_to(folder.resolve()): raise ValueError('Invalid document path.')
    if path.stat().st_size>512000: raise ValueError('Document is too large for this reader.')
    return {**paper, 'project':project, 'content':path.read_text(encoding='utf-8')}
