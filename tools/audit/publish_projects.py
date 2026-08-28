# -*- coding: utf-8 -*-
"""세 프로젝트 웹 표준 감사 결과를 상세 페이지 칸에 박는다.

값은 `project_audit.js` 가 쓴 `projects.json` 에서만 온다. 손으로 옮겨 적지 않는다.

  python tools/audit/publish_projects.py        칸을 채운다
  python tools/audit/publish_projects.py --dry  무엇이 들어가는지만 본다

W3C 오류는 「렌더 후」 값을 쓴다. 서버가 준 본문만 검사하면 SPA 는 껍데기를 보고
오류 0 을 돌려준다. 통과한 게 아니라 화면을 안 본 것이다. 그래서 검사한 바이트 수도
같이 실어 「정말 봤는지」를 지면에서 확인할 수 있게 한다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA = os.path.join(HERE, 'projects.json')

PAGES = {
    'triplinker': 'projects/triplinker.html',
    'cogi': 'projects/cogi.html',
    'omong': 'projects/omong.html',
}


def fill(html, prefix, vals):
    hit, miss = 0, []

    def one(m):
        nonlocal hit
        tag, attrs, key = m.group(1), m.group(2), m.group(3)
        if not key.startswith(prefix + '.'):
            return m.group(0)
        short = key[len(prefix) + 1:]
        if short not in vals:
            miss.append(short)
            return m.group(0)
        hit += 1
        v = vals[short]
        if short.endswith('.bar'):
            a2 = re.sub(r'style="[^"]*"', 'style="width:%s"' % v, attrs)
            if 'style=' not in a2:
                a2 += ' style="width:%s"' % v
            return '<%s%s></%s>' % (tag, a2, tag)
        return '<%s%s>%s</%s>' % (tag, attrs, v, tag)

    out = re.sub(r'<(\w+)([^>]*data-m="([^"]+)"[^>]*)>.*?</\1>', one, html, flags=re.S)
    return out, hit, miss


def numbers(p):
    lh, w = p['lighthouse'], p.get('w3cRendered') or {}
    v = {
        'at': None,
        'url': p['url'],
        'kind': p['kind'],
    }
    for k, short in (('performance', 'perf'), ('accessibility', 'a11y'),
                     ('bestPractices', 'bp'), ('seo', 'seo')):
        v[short] = str(lh[k])
        v[short + '.bar'] = '%d%%' % lh[k]
        v[short + '.spread'] = lh['spread'][k]
    v['lcp'] = lh['lcp']
    v['cls'] = lh['cls']
    v['tbt'] = lh['tbt']
    v['w3c'] = '—' if w.get('errors') is None else '%d건' % w['errors']
    v['w3c.n'] = '—' if w.get('errors') is None else str(w['errors'])
    v['w3c.rules'] = '—' if w.get('rules') is None else '%d종' % w['rules']
    v['w3c.bytes'] = '—' if not w.get('bytes') else '{:,}B'.format(w['bytes'])
    v['shell.bytes'] = '—' if not p.get('htmlBytes') else '{:,}B'.format(p['htmlBytes'])
    tops = w.get('top') or []
    for i, t in enumerate(tops[:3], 1):
        v['top%d.n' % i] = '%d회' % t['n']
        v['top%d.msg' % i] = t['msg']
    return v


def main():
    dry = '--dry' in sys.argv
    d = json.loads(io.open(DATA, encoding='utf-8').read())
    v_at = d.get('at', '')
    runs = d.get('runs', 3)
    for key, page in PAGES.items():
        p = d['projects'].get(key)
        if not p:
            print('  %-10s 감사 결과 없음 — 건너뜀' % key)
            continue
        vals = numbers(p)
        vals['at'] = v_at.replace('-', '.')
        vals['runs'] = '%d회' % runs
        path = os.path.join(SITE, page)
        html = io.open(path, encoding='utf-8').read()
        out, hit, miss = fill(html, 'pa', vals)
        print('  %-10s %2d칸 채움%s' % (key, hit,
              ('  (값 없음: %s)' % ', '.join(sorted(set(miss))[:6])) if miss else ''))
        if dry:
            for k in sorted(vals):
                print('        %-16s %s' % (k, vals[k]))
        elif out != html:
            io.open(path, 'w', encoding='utf-8', newline='').write(out)
    if dry:
        print('  --dry 라 파일은 안 건드렸다')
    return 0


if __name__ == '__main__':
    sys.exit(main())
