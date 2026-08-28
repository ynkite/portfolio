# -*- coding: utf-8 -*-
"""05 절에서 연결어미 뒤 쉼표를 찾는다.

정규식은 metrics.py 의 ending_comma_rate 와 같은 것을 쓴다.
지표가 세는 것과 내가 찾는 것이 다르면 고쳐도 값이 안 내려간다.
"""
import io, re, html
ENDINGS = r"(?:고|며|지만|면서|아서|어서)"
for f in ('triplinker', 'cogi', 'omong'):
    s = io.open('projects/%s.html' % f, encoding='utf-8').read()
    a = s.index('05 &middot; DEVELOPMENT') if '05 &middot; DEVELOPMENT' in s else s.index('05 · DEVELOPMENT')
    b = s.index('06 &middot; DEPLOY') if '06 &middot; DEPLOY' in s else s.index('06 · DEPLOY')
    hits = []
    for m in re.finditer(r'<p class="(?:evnote|lead rv)"[^>]*>(.*?)</p>'
                         r'|<div class="n">[^<]*</div>\s*<h3>[^<]*</h3>\s*<p>(.*?)</p>'
                         r'|<td class="ch">(.*?)</td>', s[a:b], re.S):
        t = html.unescape(re.sub(r'<[^>]+>', '', m.group(1) or m.group(2) or m.group(3) or ''))
        t = re.sub(r'\s+', ' ', t).strip()
        for mm in re.finditer(ENDINGS + r"\s*,", t):
            hits.append('…%s…' % t[max(0, mm.start() - 44):min(len(t), mm.end() + 30)])
    print('== %s : %d' % (f, len(hits)))
    for h in hits:
        print('   ' + h)
