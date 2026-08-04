# -*- coding: utf-8 -*-
"""manifest.py가 고른 파일만 저장소 작업 트리에 옮긴다.

목록에 없는 사이트 파일은 지워 저장소가 곧 사이트가 되게 한다.
사용 — python tools/sync_repo.py <저장소경로>
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest import plan, ROOT


def main(dst):
    os.chdir(ROOT)
    keep = set(plan()[0])

    removed = []
    for top in ('assets', 'projects'):
        d = os.path.join(dst, top)
        if not os.path.isdir(d):
            continue
        for r, _, fs in os.walk(d):
            for x in fs:
                rel = os.path.relpath(os.path.join(r, x), dst).replace(os.sep, '/')
                if rel not in keep:
                    removed.append(rel)

    for p in sorted(keep):
        t = os.path.join(dst, p)
        os.makedirs(os.path.dirname(t) or dst, exist_ok=True)
        shutil.copy2(p, t)

    for rel in removed:
        fp = os.path.join(dst, rel)
        if os.path.exists(fp):
            os.remove(fp)

    print('복사 %d개 / 루트에서 제거 %d개' % (len(keep), len(removed)))
    for rel in removed:
        print('   -', rel)


if __name__ == '__main__':
    main(sys.argv[1])
