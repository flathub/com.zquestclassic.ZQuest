#!/usr/bin/env python3
"""Check that the manifest's dependency pins match upstream's CMakeLists.txt.

The manifest vendors ZQuest Classic's dependencies as separate sources, pinned
to the same commits upstream pins with FetchContent_Declare. Upstream bumps
those pins in some releases, so after updating the zquest source (by hand or
via flatpak-external-data-checker), run this to find pins that need updating.

Usage: check_deps.py [manifest.yml]
"""

import re
import sys
import urllib.request

import yaml

MANIFEST = sys.argv[1] if len(sys.argv) > 1 else 'com.zquestclassic.ZQuest.yml'
UPSTREAM_REPO = 'https://github.com/ZQuestClassic/ZQuestClassic'
# Upstream dependencies the flatpak intentionally does not vendor.
NOT_VENDORED = {'sentry', 'asio', 'websocketpp'}


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

    if errors:
        print('\nDependency pins out of date:')
        for e in errors:
            print(f'  - {e}')
        sys.exit(1)
    print('All dependency pins match upstream.')


if __name__ == '__main__':
    main()
