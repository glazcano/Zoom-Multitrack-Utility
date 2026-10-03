from pathlib import Path


def project_files(folder, recursive=False):
    folder = Path(folder)
    items = folder.rglob('*') if recursive else folder.iterdir()
    return sorted((p for p in items if p.is_file() and p.suffix.casefold() == '.h8prj'
                   and not p.name.startswith('._')), key=lambda p: str(p).casefold())
