"""Validate four native packages and attach them to an unpublished release."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from h8studio import __version__


def release_assets(folder, version):
    expected = [f'H8Studio-{version}-{suffix}' for suffix in (
        'windows-x86_64.zip', 'fedora-x86_64.tar.gz', 'macos-arm64.zip', 'macos-x86_64.zip')]
    assets = []
    for name in expected:
        matches = list(Path(folder).rglob(name))
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one native package: {name}')
        archive = matches[0]
        checksum = archive.with_name(name+'.sha256')
        fields = checksum.read_text(encoding='utf-8').strip().split()
        digest = hashlib.sha256()
        with archive.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                digest.update(chunk)
        if fields != [digest.hexdigest(), name]:
            raise ValueError(f'Checksum mismatch: {name}')
        assets.extend((archive, checksum))
    return assets


def validate_existing(release, commit):
    if not release['isDraft']:
        raise ValueError('This version is already published. Increase the app version; published assets are never replaced.')
    if release['targetCommitish'] != commit:
        raise ValueError('The existing draft belongs to another commit. Increase the app version or remove that draft explicitly.')


def main():
    assets = release_assets(sys.argv[1], __version__)
    tag, commit, repo = 'v'+__version__, os.environ['GITHUB_SHA'], os.environ['GITHUB_REPOSITORY']
    base = ['gh', 'release']
    existing = subprocess.run(base+['view', tag, '--repo', repo, '--json', 'isDraft,targetCommitish'], capture_output=True, text=True)
    if existing.returncode == 0:
        validate_existing(json.loads(existing.stdout), commit)
    else:
        # Refuse to reuse an existing tag: a draft must point at the exact build.
        ref = subprocess.run(['gh', 'api', f'repos/{repo}/git/ref/tags/{tag}'], capture_output=True, text=True)
        if ref.returncode == 0:
            raise ValueError('This tag already exists without a matching draft. Choose a new version.')
        subprocess.run(base+['create', tag, '--repo', repo, '--draft', '--target', commit,
                            '--title', f'H8 Studio {__version__}', '--notes-file', str(ROOT/'docs/release-notes.md')], check=True)
    subprocess.run(base+['upload', tag, '--repo', repo, '--clobber']+[str(p) for p in assets], check=True)
    subprocess.run(base+['view', tag, '--repo', repo, '--json', 'url,isDraft'], check=True)


if __name__ == '__main__':
    main()
