# -*- coding: utf-8 -*-
"""트러블슈팅 카드(원인 · 해결)의 줄바꿈을 PDF 와 같은 규칙으로 맞춘다.

카드가 좁아 그냥 두면 「질의 첫 / 토큰을」 처럼 구 한가운데서 접힌다.
문장 끝에서 먼저 끊고, 그래도 길면 절이 끝나는 자리에서 한 번 더 끊는다.
PDF 쪽은 기존 <br> 를 지우고 같은 규칙을 다시 걸므로 두 번 끊기지 않는다.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from build_summary import sentence_breaks

PAGES = ('projects/cogi.html', 'projects/triplinker.html', 'projects/omong.html')
# 원인 · 해결 칸의 본문만 고른다
BLK = re.compile(r'(<div class="b(?: res)?">\s*<div class="lab">[^<]*</div>\s*<p>)(.*?)(</p>)', re.S)


def main():
    total = 0
    for rel in PAGES:
        p = os.path.join(ROOT, rel)
        s = io.open(p, encoding='utf-8').read()
        n = [0]

        def fix(m):
            body = re.sub(r'<br\s*/?>', ' ', m.group(2))
            body = re.sub(r'\s+', ' ', body).strip()
            out = sentence_breaks(body)
            if out != m.group(2):
                n[0] += 1
            return m.group(1) + out + m.group(3)

        s = BLK.sub(fix, s)
        io.open(p, 'w', encoding='utf-8', newline='').write(s)
        total += n[0]
        print('  %-26s %d칸' % (rel, n[0]))
    print('  모두 %d칸' % total)


if __name__ == '__main__':
    main()
