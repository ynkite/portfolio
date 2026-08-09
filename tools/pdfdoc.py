# -*- coding: utf-8 -*-
"""사이트에서 '내용'만 구조로 뽑아 온다.

마크업을 통째로 옮기면 웹 화면의 습관(전폭 목록, 뷰포트 기준 목업)이
지면으로 따라와 캡처를 늘어놓은 꼴이 된다. 그래서 문단·카드·표·항목을
자료로 뽑아 두고, 조판은 지면 규격에 맞춰 새로 짠다.
디자인은 사이트 컴포넌트를 그대로 다시 그려 붙인다.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    return io.open(os.path.join(ROOT, p), encoding='utf-8').read()


def one(pat, s, d=''):
    m = re.search(pat, s, re.S)
    return m.group(1).strip() if m else d


def grab(s, opener, tag='div'):
    """opener로 시작하는 요소 하나를 통째로 떼어 온다."""
    i = s.index(opener)
    depth, j = 0, i
    for m in re.finditer(r'<%s\b|</%s>' % (tag, tag), s[i:]):
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                j = i + m.end()
                break
        else:
            depth += 1
    return s[i:j]


def children(el, tag='div'):
    """요소의 최상위 자식들을 문자열로 낸다."""
    body = el[el.index('>') + 1:el.rindex('</')]
    out, i, n = [], 0, len(body)
    while i < n:
        m = re.compile(r'<([a-zA-Z][\w-]*)').search(body, i)
        if not m:
            break
        t = m.group(1).lower()
        gt = body.index('>', m.end())
        if t in ('img', 'br', 'hr') or body[gt - 1] == '/':
            out.append(body[m.start():gt + 1])
            i = gt + 1
            continue
        depth, j = 1, gt + 1
        pat = re.compile(r'<%s\b|</%s\s*>' % (t, t), re.I)
        while depth and j < n:
            k = pat.search(body, j)
            if not k:
                j = n
                break
            depth += -1 if k.group(0).startswith('</') else 1
            j = k.end()
        out.append(body[m.start():j])
        i = j
    return [x for x in out if x.strip()]


# ─────────────────────────── 상세 페이지 ───────────────────────────

def parse_block(el):
    """섹션 안의 덩어리 하나를 자료로 바꾼다."""
    cls = one(r'class="([^"]*)"', el[:el.index('>') + 1])
    names = cls.split()
    if 'cards' in names:
        return {'t': 'cards', 'items': children(el)}
    if 'dtable' in names:
        return {'t': 'dtable', 'items': children(el)}
    if 'ts' in names:
        return {'t': 'ts', 'items': children(el)}
    if 'parts' in names:
        return {'t': 'parts', 'items': children(el)}
    if 'feats' in names:
        return {'t': 'feats', 'items': children(el)}
    if 'press' in names:
        return {'t': 'press', 'items': children(el)}
    if 'figure' in names:
        return {'t': 'figure',
                'src': one(r'src="([^"]+)"', el).replace('../assets/', 'assets/'),
                'cap': one(r'<div class="cap">(.*?)</div>', el)}
    if 'ov' in names:
        return {'t': 'ov', 'html': el}
    if 'docbtns' in names:
        return {'t': 'docs'}
    if 'videowrap' in names or 'videocap' in names or 'videosec' in names:
        return None
    if el.startswith('<p'):
        return {'t': 'prose', 'html': el}
    return {'t': 'raw', 'html': el}


def project(path):
    """상세 페이지 한 장을 통째로 자료로 만든다."""
    s = read(path)
    head = s[s.index('<header class="phead">'):s.index('</header>')]
    out = {
        'kick': one(r'<div class="cat">(.*?)</div>', head),
        'name': one(r'<h1>(.*?)</h1>', head),
        'desc': one(r'<p class="desc">(.*?)</p>', head),
        'meta': one(r'<div class="meta">(.*?)</div>', head),
        'chips': grab(head, '<div class="chips">'),
        'links': grab(head, '<div class="links">'),
        'sections': [],
    }
    body = s[s.index('</header>'):s.index('<div class="foot">')]
    for sec in re.findall(r'<section>.*?</section>', body, re.S):
        w = grab(sec, '<div class="wrap">')
        item = {'step': one(r'<div class="step">(.*?)</div>', w),
                'title': one(r'<h2[^>]*>(.*?)</h2>', w),
                'rline': one(r'<div class="rline[^"]*">(.*?)</div>', w),
                'lead': '', 'blocks': []}
        for el in children(w):
            if 'class="step"' in el or el.startswith('<h2'):
                continue
            if 'class="rline' in el[:40]:
                continue
            if el.startswith('<p') and 'lead' in el[:30] and not item['lead']:
                item['lead'] = one(r'<p[^>]*>(.*?)</p>', el)
                continue
            b = parse_block(el)
            if b:
                item['blocks'].append(b)
        out['sections'].append(item)
    return out


# ─────────────────────────── 메인 페이지 ───────────────────────────

def index_parts():
    s = read('index.html')
    out = {}
    top = s[s.index('<section class="about'):s.index('<section class="skills-sec')]
    out['lead'] = one(r'<p class="lead rv">(.*?)</p>', top)
    out['abgrid'] = grab(top, '<div class="abgrid')

    sk = s[s.index('<section class="skills-sec'):s.index('<section class="credits')]
    out['sknote'] = one(r'<p class="rv">(.*?)</p>', sk)
    out['skcols'] = grab(sk, '<div class="skcols')
    out['skp'] = children(grab(sk, '<div class="skpanel'))

    cr = s[s.index('<section class="credits'):s.index('<section class="feat gray')]
    out['folds'] = [x for x in children(grab(cr, '<div class="folds')) if '<details' in x]

    out['feat'] = {}
    for key in ('work', 'triplinker', 'omong'):
        i = s.index('id="%s"' % key)
        sec = s[i:s.index('</section>', i)]
        w = grab(sec, '<div class="wrap">')
        out['feat'][key] = {
            'device': grab(w, '<div class="device'),
            'hl': [x for x in children(w) if 'class="hl' in x[:30]],
            'bullets': grab(w, '<ul class="tech"', 'ul') if '<ul class="tech"' in w else '',
            'links': grab(w, '<div class="projbtns">') if '<div class="projbtns">' in w else '',
        }

    more = s[s.index('<section class="grid-sec'):s.index('<section class="arch')]
    out['tiles'] = children(grab(more, '<div class="tiles'))

    arch = s[s.index('<section class="arch'):s.index('<div class="imglb"')]
    out['archcards'] = grab(arch, '<div class="archcards')
    return out
