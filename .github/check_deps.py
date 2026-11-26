#!/usr/bin/env python3
"""Check that the manifest's pinned sources match upstream.

The manifest vendors ZQuest Classic's dependencies as separate sources, pinned
to the same commits upstream pins with FetchContent_Declare. Upstream bumps
those pins in some releases, so after updating the zquest source (by hand or
via flatpak-external-data-checker), run this to find pins that need updating.

It also checks the file sources for the Git LFS files under resources/, which
the manifest fetches separately (the zquest source sets disable-lfs). Each must
point at the zquest source's commit and have the LFS object id as its sha256.

Usage: check_deps.py [manifest.yml]
"""

import os
import re
import subprocess
import sys
import tempfile
import urllib.request

import yaml

MANIFEST = sys.argv[1] if len(sys.argv) > 1 else 'com.zquestclassic.ZQuest.yml'
UPSTREAM_REPO = 'https://github.com/ZQuestClassic/ZQuestClassic'
# Upstream dependencies the flatpak intentionally does not vendor.
NOT_VENDORED = {'sentry', 'asio', 'websocketpp'}
LFS_URL_PREFIX = 'https://media.githubusercontent.com/media/ZQuestClassic/ZQuestClassic/'
LFS_DIR = 'resources'


def normalize_url(url):
    url = url.strip().rstrip('/').lower()
    return url[:-4] if url.endswith('.git') else url


def parse_fetchcontent(cmake):
    deps = []
    for body in re.findall(r'FetchContent_Declare\s*\((.*?)\)', cmake, re.S):
        tokens = body.split()
        dep = {'name': tokens[0].lower()}
        for key, field in (('GIT_REPOSITORY', 'repo'), ('GIT_TAG', 'tag'), ('URL', 'url')):
            if key in tokens:
                dep[field] = tokens[tokens.index(key) + 1]
        deps.append(dep)
    return deps


def git(cwd, *args, stdin=None):
    return subprocess.run(['git', '-C', cwd, *args], input=stdin, capture_output=True, text=True, check=True).stdout


def upstream_lfs_files(ref):
    """Return {path: sha256} for the LFS files under LFS_DIR at ref."""
    with tempfile.TemporaryDirectory() as d:
        git(d, 'init', '-q')
        # Fetch trees only; the few blobs needed are fetched on demand.
        git(d, 'fetch', '-q', '--depth=1', '--filter=blob:none', UPSTREAM_REPO, ref)
        paths = git(d, 'ls-tree', '-r', '--name-only', 'FETCH_HEAD', LFS_DIR)
        attrs = git(d, 'check-attr', '--source=FETCH_HEAD', '--stdin', 'filter', stdin=paths)
        files = {}
        for line in attrs.splitlines():
            path, _, value = line.rsplit(': ', 2)
            if value != 'lfs':
                continue
            pointer = git(d, 'cat-file', '-p', f'FETCH_HEAD:{path}')
            m = re.search(r'^oid sha256:([0-9a-f]{64})$', pointer, re.M)
            if not m:
                raise RuntimeError(f'{path} is marked as LFS but is not an LFS pointer')
            files[path] = m.group(1)
        return files


def check_lfs_files(sources, ref, errors):
    print(f'Checking LFS file sources against {LFS_DIR}/ at {ref}')
    expected = upstream_lfs_files(ref)
    actual = {}
    bad = set()
    for s in sources:
        url = s.get('url', '')
        if s.get('type') != 'file' or not url.startswith(LFS_URL_PREFIX):
            continue
        commit, _, path = url[len(LFS_URL_PREFIX):].partition('/')
        actual[path] = s
        if commit != ref:
            errors.append(f'{path}: file source URL uses commit {commit}, but the zquest source is at {ref}')
            bad.add(path)
        if s.get('dest') != os.path.dirname(path):
            errors.append(f'{path}: file source dest is {s.get("dest")}, expected {os.path.dirname(path)}')
            bad.add(path)

    for path, oid in sorted(expected.items()):
        source = actual.get(path)
        if source is None:
            errors.append(f'{path}: LFS file upstream has no file source in the manifest. Add:\n'
                          f'      - type: file\n'
                          f'        url: {LFS_URL_PREFIX}{ref}/{path}\n'
                          f'        sha256: {oid}\n'
                          f'        dest: {os.path.dirname(path)}')
        elif source.get('sha256') != oid:
            errors.append(f'{path}: file source sha256 is {source.get("sha256")}, upstream LFS object is {oid}')
        elif path not in bad:
            print(f'  ok  {path} {oid[:12]}')
    for path in sorted(set(actual) - set(expected)):
        errors.append(f'{path}: file source in the manifest, but it is not an LFS file upstream')


def main():
    with open(MANIFEST) as f:
        manifest = yaml.safe_load(f)
    module = next(m for m in manifest['modules'] if m['name'] == 'zquest')
    sources = module['sources']
    main_source = next(s for s in sources if normalize_url(s.get('url', '')) == normalize_url(UPSTREAM_REPO))
    tag = main_source.get('tag')
    ref = main_source.get('commit') or tag
    errors = []

    release_tag = next((o.split('=', 1)[1] for o in module.get('config-opts', []) if 'RELEASE_TAG=' in o), None)
    if release_tag != tag:
        errors.append(f'RELEASE_TAG config-opt is {release_tag}, but the zquest source tag is {tag}')

    raw_url = f'https://raw.githubusercontent.com/ZQuestClassic/ZQuestClassic/{ref}/CMakeLists.txt'
    print(f'Checking dependency pins against {raw_url}')
    with urllib.request.urlopen(raw_url) as r:
        upstream = parse_fetchcontent(r.read().decode())

    by_url = {}
    for s in sources:
        if s is main_source or 'url' not in s:
            continue
        by_url[normalize_url(s['url'])] = s

    for dep in upstream:
        key = normalize_url(dep.get('repo') or dep.get('url', ''))
        source = by_url.get(key)
        if source is None:
            if dep['name'] not in NOT_VENDORED:
                errors.append(f'{dep["name"]}: upstream uses {key}, which is not in the manifest')
            continue
        if 'repo' in dep:
            pinned = {source.get('commit'), source.get('tag')}
            if dep.get('tag') not in pinned:
                errors.append(f'{dep["name"]}: upstream pins {dep.get("tag")}, manifest has {source.get("commit") or source.get("tag")}')
            else:
                print(f'  ok  {dep["name"]} {dep["tag"]}')
        else:
            print(f'  ok  {dep["name"]} {dep["url"]}')

    check_lfs_files(sources, ref, errors)

    if errors:
        print('\nOut of date:')
        for e in errors:
            print(f'  - {e}')
        sys.exit(1)
    print('All dependency pins and LFS file sources match upstream.')


if __name__ == '__main__':
    main()
