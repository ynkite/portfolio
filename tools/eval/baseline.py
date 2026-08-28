# -*- coding: utf-8 -*-
"""같은 조건을 모델에 그냥 던져 보고 서비스와 나란히 놓는다.

TripLinker 는 장소 후보를 카카오 검색 결과에서만 고른다. 그 장치가 실제로
무엇을 벌어 주는지는 「없을 때」와 비교해야 나온다. 그래서 같은 여행 조건을
모델에게 맨몸으로 던지고, 나온 장소 이름을 같은 방법으로 카카오에 조회한다.

  python tools/eval/baseline.py            앞 20건
  python tools/eval/baseline.py --n 40     건수 지정
"""
import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROPS = r'E:\daewooproject\trip-linker\src\main\resources\application.properties'
OUT = os.path.join(HERE, 'runs', 'baseline.json')

cfg = io.open(PROPS, encoding='utf-8', errors='replace').read()


def prop(k, default=''):
    m = re.search(re.escape(k) + r'=(.*)', cfg)
    return m.group(1).strip() if m else default


GROQ_KEY = prop('spring.ai.openai.api-key')
GROQ_URL = prop('spring.ai.openai.base-url', 'https://api.groq.com/openai') + '/v1/chat/completions'
MODEL = prop('spring.ai.openai.chat.options.model', 'llama-3.3-70b-versatile')
if '--model' in sys.argv:
    MODEL = sys.argv[sys.argv.index('--model') + 1]
KAKAO_KEY = prop('kakao.rest.api.key')

PROMPT = """너는 여행 일정을 짜는 도우미다. 아래 조건으로 일정을 만들어라.

목적지: %(destination)s
기간: %(startDate)s ~ %(endDate)s (%(nights)d박)
출발지: %(departure)s
이동수단: %(transportType)s
숙소: %(accommodationType)s
동행: %(companionType)s %(companionCount)s명
스타일: %(travelStyles)s
일정 밀도: %(scheduleDensity)s
예산: %(budget)s원

JSON 으로만 답하라. 다른 말은 쓰지 마라.
{"days":[{"day":1,"places":[{"name":"장소 이름","cost":0}]}]}
name 은 실제로 있는 상호나 장소 이름이어야 한다. cost 는 1인 기준 원 단위 숫자다."""


def ask(row):
    nights = (_d(row['endDate']) - _d(row['startDate']))
    body = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'user', 'content': PROMPT % dict(row, nights=nights)}],
        'temperature': 0.7,
    }, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(GROQ_URL, data=body, headers={
        'Authorization': 'Bearer ' + GROQ_KEY,
        'Content-Type': 'application/json',
        # 기본 User-Agent(Python-urllib)는 Cloudflare 가 1010 으로 막는다
        'User-Agent': 'triplinker-eval/1.0'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        obj = json.loads(r.read().decode('utf-8'))
    ms = int((time.time() - t0) * 1000)
    return obj['choices'][0]['message']['content'], ms


def _d(s):
    import datetime
    return datetime.date(*[int(x) for x in s.split('-')]).toordinal()


FENCE = re.compile(r'^```[a-zA-Z]*\s*|\s*```$', re.M)


def parse(text):
    s = FENCE.sub('', text or '').strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r'\{.*\}', s, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except Exception:
            return None


_cache = {}


def in_kakao(dest, name):
    k = (dest, name)
    if k in _cache:
        return _cache[k]
    url = ('https://dapi.kakao.com/v2/local/search/keyword.json?size=5&query='
           + urllib.parse.quote('%s %s' % (dest, name)))
    req = urllib.request.Request(url, headers={'Authorization': 'KakaoAK ' + KAKAO_KEY})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            docs = json.loads(r.read().decode('utf-8')).get('documents', [])
    except Exception:
        docs = []
    ok = any(dest in (d.get('address_name') or '') or dest in (d.get('road_address_name') or '')
             for d in docs)
    _cache[k] = ok
    return ok


def main():
    n = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 20
    rows = list(csv.DictReader(io.open(os.path.join(HERE, 'sets', 'triplinker-route.csv'),
                                       encoding='utf-8-sig', newline='')))[:n]
    out = []
    places_total = places_found = 0
    for i, row in enumerate(rows, 1):
        rec = {'id': row['id'], 'destination': row['destination']}
        try:
            text, ms = ask(row)
        except Exception as e:
            rec.update(ok=False, why='호출 실패 %s' % e)
            out.append(rec)
            continue
        rec['ms'] = ms
        obj = parse(text)
        if not obj or not obj.get('days'):
            rec.update(ok=False, why='JSON 아님')
            out.append(rec)
            continue
        names = [p.get('name') for d in obj['days'] for p in (d.get('places') or []) if p.get('name')]
        cost = sum(int(p.get('cost') or 0) for d in obj['days'] for p in (d.get('places') or [])
                   if str(p.get('cost') or '').lstrip('-').isdigit())
        found = sum(1 for nm in names if in_kakao(row['destination'], nm))
        want_days = _d(row['endDate']) - _d(row['startDate']) + 1
        rec['names'] = names          # 교차 검증에 쓰려면 이름이 남아 있어야 한다
        rec.update(ok=True, places=len(names), found=found,
                   days=len(obj['days']), want_days=want_days,
                   cost=cost, budget=int(row['budget']))
        places_total += len(names)
        places_found += found
        out.append(rec)
        sys.stdout.write('\r  %d/%d' % (i, len(rows)))
        sys.stdout.flush()
    print()

    ok = [r for r in out if r.get('ok')]
    ms = sorted(r['ms'] for r in ok)
    summary = {
        'model': MODEL,
        'n': len(rows),
        'json_ok': len(ok),
        'places': places_total,
        'places_found': places_found,
        'found_rate': round(100.0 * places_found / places_total, 1) if places_total else 0,
        'days_match': sum(1 for r in ok if r['days'] == r['want_days']),
        'budget_ok': sum(1 for r in ok if r['cost'] and r['cost'] <= r['budget']),
        'budget_reported': sum(1 for r in ok if r['cost']),
        'median_ms': ms[len(ms) // 2] if ms else 0,
    }
    io.open(OUT, 'w', encoding='utf-8', newline='').write(
        json.dumps({'summary': summary, 'rows': out}, ensure_ascii=False, indent=1))

    print('모델 %s · %d건' % (MODEL, len(rows)))
    print('  JSON 으로 답한 건      %d/%d' % (summary['json_ok'], len(rows)))
    print('  장소 실재율            %.1f%% (%d/%d)' % (summary['found_rate'], places_found, places_total))
    print('  일수 일치              %d/%d' % (summary['days_match'], len(ok)))
    print('  예산 안에 든 건        %d/%d (비용을 적은 건 %d)' %
          (summary['budget_ok'], len(ok), summary['budget_reported']))
    print('  응답 시간 중앙값       %dms' % summary['median_ms'])
    print('-> %s' % os.path.relpath(OUT, HERE))
    return 0


if __name__ == '__main__':
    sys.exit(main())
