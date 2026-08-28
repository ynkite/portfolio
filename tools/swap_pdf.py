# -*- coding: utf-8 -*-
"""새로 뽑은 PDF 를 최종 이름으로 올린다.

크롬이나 PDF 뷰어가 최종 파일을 열고 있으면 윈도가 덮어쓰기를 막는다.
그럴 때 빌더는 새 판을 `*.pdf.new` 로 남긴다. 뷰어를 닫은 뒤 이 스크립트를 돌리면
새 판이 최종 이름을 갖는다.

  python tools/swap_pdf.py
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')


def pages(path):
    try:
        d = io.open(path, 'rb').read()
        import re
        return len(re.findall(rb'/MediaBox', d))
    except Exception:
        return 0


def main():
    done = skip = 0
    for f in sorted(os.listdir(OUT)):
        if not f.endswith('.pdf.new'):
            continue
        new = os.path.join(OUT, f)
        final = new[:-4]
        try:
            os.replace(new, final)
            print('  올렸다  %s  (%d쪽 · %.1fMB)'
                  % (os.path.basename(final), pages(final), os.path.getsize(final) / 1048576.0))
            done += 1
        except OSError as e:
            print('  막혔다  %s — %s' % (os.path.basename(final), e.strerror))
            print('          %s 를 여는 뷰어(크롬 탭 포함)를 닫고 다시 돌린다.' % os.path.basename(final))
            skip += 1
    if not done and not skip:
        print('  올릴 새 판이 없다. 이미 최신이다.')
    return 1 if skip else 0


if __name__ == '__main__':
    sys.exit(main())
