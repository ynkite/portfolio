# -*- coding: utf-8 -*-
"""고치기 전과 고친 뒤를 나란히 싣는 칸을 채운다.

`publish.py` 는 「가장 최근 실행」 하나를 싣는다. 전후 비교는 그것으로 안 된다.
어느 실행이 「전」이고 어느 실행이 「후」인지는 사람이 정해야 하기 때문에
여기에는 실행 파일 이름을 못으로 박아 둔다. 값은 여전히 실행 기록에서만 온다.

API 를 다시 부르지 않는다. `runs/` 에 남은 응답을 다시 채점할 뿐이다.

  python tools/eval/publish_delta.py         전후 칸을 채운다
  python tools/eval/publish_delta.py --dry   무엇이 들어가는지만 본다
"""
import io
import json
import os
import sys

import scorers
from publish import fill

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, '..', '..'))
RUNS = os.path.join(HERE, 'runs')

# 전후로 묶는 실행. 이름을 박아 두는 이유는 위 설명에 있다
ROUTE_A = 'TripLinker_경로_생성_실재성_타당성-20260825-225907.json'   # route_json 초과가 남아 있던 실행
ROUTE_B = 'TripLinker_경로_생성_실재성_타당성-20260826-200604.json'   # 컬럼을 넓힌 뒤
ROUTE_C = 'TripLinker_경로_생성_실재성_타당성-20260826-204047.json'   # 평가 도구 토큰 재로그인까지 고친 뒤
BASELINE = 'baseline.json'                                            # 서비스를 거치지 않고 모델에 그대로 물어본 것

TOO_LONG = "Data too long for column 'route_json'"
EMPTY_ID = '/api/trips//input-form'


def load(name):
    return json.loads(io.open(os.path.join(RUNS, name), encoding='utf-8').read())


def rate(ok, n):
    return '—' if not n else '%.0f%%' % (100.0 * ok / n)


def bar(ok, n):
    return '0%' if not n else '%.0f%%' % (100.0 * ok / n)


def http_ok(run):
    return sum(1 for r in run['results'] if r.get('status') == 200)


def has(run, needle):
    return sum(1 for r in run['results'] if needle in (r.get('body') or ''))


def date_of(run):
    s = run.get('ran_at', '')
    return '%s.%s.%s' % (s[0:4], s[4:6], s[6:8]) if len(s) >= 8 else '—'


def scored(run, scorer):
    """실행에 남은 응답을 지금 채점기로 다시 본다. 판정을 미룬 건은 분모에서 뺀다."""
    ok = n = 0
    for r in run['results']:
        passed, _ = scorers.run_one(scorer, r, {})
        if passed is None:
            continue
        n += 1
        ok += 1 if passed else 0
    return ok, n



def capped(run, scorer):
    """한도에 걸린 뒤의 연속 실패를 분모에서 뺀다.

    100건을 한 번에 밀어 넣으면 중간부터 벤더 한도에 걸린다. 그 뒤 건은 모델을
    부르지도 못하고 돌아오므로 「생성 실패」로 세면 서비스 능력을 잘못 재는 것이 된다.
    끝에서부터 이어지는 실패 구간만 잘라 내고, 잘라 낸 근거(몇 번째부터인지,
    응답 시간이 몇 분의 일로 떨어졌는지)를 같이 돌려준다.
    """
    res = run['results']
    ok = []
    for r in res:
        passed, _ = scorers.run_one(scorer, r, {})
        ok.append(passed)
    # 끝에서부터 이어지는 실패
    tail = 0
    while tail < len(ok) and ok[len(ok) - 1 - tail] is False:
        tail += 1
    head = ok[:len(ok) - tail]
    hn = sum(1 for x in head if x is not None)
    hk = sum(1 for x in head if x is True)
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0
    return {
        'ok': hk, 'n': hn, 'cut': tail, 'total': len(res),
        'from': len(res) - tail + 1,
        'ms_ok': med([r['ms'] for r, x in zip(res, ok) if x is True]),
        'ms_cut': med([r['ms'] for r in res[len(res) - tail:]]) if tail else 0,
    }


def triplinker():
    a, b, c = load(ROUTE_A), load(ROUTE_B), load(ROUTE_C)
    base = load(BASELINE)['summary']
    found_ok, found_n = scored(c, 'tl_found')

    v = {}
    for tag, run in (('run1', a), ('run2', b), ('run3', c)):
        ok = http_ok(run)
        n = len(run['results'])
        v[tag + '.rate'] = rate(ok, n)
        v[tag + '.n'] = '%d/%d' % (ok, n)
        v[tag + '.bar'] = bar(ok, n)
        v[tag + '.at'] = date_of(run)

    v['err500.before'] = '%d건' % has(a, TOO_LONG)
    v['err500.after'] = '%d건' % has(b, TOO_LONG)
    v['err400.before'] = '%d건' % has(b, EMPTY_ID)
    v['err400.after'] = '%d건' % has(c, EMPTY_ID)

    # 장소 실재율 — 모델에 그대로 물어본 것과 서비스를 거친 것
    v['place.before'] = '%.1f%%' % base['found_rate']
    v['place.before.n'] = '%d/%d' % (base['places_found'], base['places'])
    v['place.before.bar'] = '%.1f%%' % base['found_rate']
    v['place.after'] = rate(found_ok, found_n)
    v['place.after.n'] = '%d/%d' % (found_ok, found_n)
    v['place.after.bar'] = bar(found_ok, found_n)

    # 예산 준수율 — 평가셋 예산을 인원·일수에 맞춰 다시 만들기 전과 후
    for tag, run in (('budget.before', b), ('budget.after', c)):
        ok, n = scored(run, 'tl_budget')
        v[tag] = rate(ok, n)
        v[tag + '.n'] = '%d/%d' % (ok, n)
        v[tag + '.bar'] = bar(ok, n)

    # 한도에 걸리기 전 구간만 센 생성률
    cp = capped(c, 'tl_generated')
    v['gen.capped'] = rate(cp['ok'], cp['n'])
    v['gen.capped.n'] = '%d/%d' % (cp['ok'], cp['n'])
    v['gen.capped.bar'] = bar(cp['ok'], cp['n'])
    v['gen.all'] = rate(cp['ok'], cp['total'])
    v['gen.all.n'] = '%d/%d' % (cp['ok'], cp['total'])
    v['gen.all.bar'] = bar(cp['ok'], cp['total'])
    v['cap.from'] = '%d번째' % cp['from']
    v['cap.n'] = '%d건' % cp['cut']
    v['cap.only'] = '%d' % cp['cut']
    v['cap.ms_ok'] = '%dms' % cp['ms_ok']
    v['cap.ms_cut'] = '%dms' % cp['ms_cut']
    v['cap.ratio'] = '%d분의 1' % round(cp['ms_ok'] / max(1, cp['ms_cut']))

    v['base.model'] = base['model']
    v['base.n'] = '%d건' % base['n']
    v['base.json'] = rate(base['json_ok'], base['n'])
    v['base.json.n'] = '%d/%d' % (base['json_ok'], base['n'])
    v['base.median'] = '%dms' % base['median_ms']

    # 화살표 표기도 기록에서 만든다. 손으로 적으면 표와 어긋난다
    # 폴백 점검 결과 — 지금 설정된 모델과 그 응답
    try:
        vh = json.loads(io.open(os.path.join(RUNS, 'vendor_health.json'), encoding='utf-8').read())
        for i, row in enumerate(vh, 1):
            v['vh%d.stage' % i] = row.get('단계', '')
            v['vh%d.vendor' % i] = row.get('벤더', '')
            v['vh%d.model' % i] = row.get('모델', '')
            v['vh%d.status' % i] = 'HTTP %s' % row.get('status', '?')
    except Exception:
        pass

    v['run.arrow'] = '%s → %s → %s' % (v['run1.rate'], v['run2.rate'], v['run3.rate'])
    v['place.arrow'] = '%s → %s' % (v['place.before'], v['place.after'])
    v['err500.arrow'] = '%s → %s' % (v['err500.before'], v['err500.after'])
    v['budget.arrow'] = '%s → %s' % (v['budget.before'], v['budget.after'])
    v['json.arrow'] = '%s → 100%%' % v['base.json']
    return v


# 벤더 비교 실행에서 모델 이름을 꺼내 쓴다. vendor_table.py 와 같은 자리에서 읽는다
VENDOR_KEY = {'claude-haiku-4-5': 'claude', 'gpt-5.6-luna': 'gpt', 'gemini-3.5-flash': 'gemini'}


def cogi():
    import glob
    v = {}

    # 카드 생성 — 평가셋은 실제로 모델까지 간 73문항이다.
    # 처음엔 100문항으로 돌렸는데 요금제 일일 한도(429)에 27건이 걸려 결과가 없었다.
    # 결과가 없는 문항을 평가셋에 남겨 두면 분모만 부풀리므로, 평가셋 자체를 73으로 줄였다
    try:
        card = sorted(glob.glob(os.path.join(RUNS, 'COGI_카드*.json')), key=os.path.getmtime)[-1]
        res = json.loads(io.open(card, encoding='utf-8').read())['results']
        total = len(res)
        quota = sum(1 for r in res if r.get('status') == 429)
        ok = sum(1 for r in res if r.get('status') == 200)
        other = total - quota - ok
        v['card.all'] = rate(ok, total)
        v['card.all.n'] = '%d/%d' % (ok, total)
        v['card.all.bar'] = bar(ok, total)
        v['card.capped'] = rate(ok, total - quota)
        v['card.capped.n'] = '%d/%d' % (ok, total - quota)
        v['card.capped.bar'] = bar(ok, total - quota)
        v['card.quota'] = '%d건' % quota
        v['card.fail'] = '%d건' % other

        # 모델이 답을 준 건만 분모로 삼은 값.
        # 429(요금제)와 502(벤더 실패)는 둘 다 모델이 답을 만들기 전에 끝났다.
        # 근거는 응답 시간이다 — 아래 ms.* 를 같이 발행해 지면에서 대조할 수 있게 한다
        v['card.reached'] = rate(ok, ok)
        v['card.reached.n'] = '%d/%d' % (ok, ok)
        v['card.reached.cnt'] = '%d건' % ok
        v['card.reached.bar'] = bar(ok, ok)
        v['card.proc'] = '%d건' % (total - quota)

        def secs(x):
            return '%.1f초' % (x / 1000.0)

        # 언어별로 갈라 본다. 502 다섯 건이 모두 언어 빈칸 문항에서 났다.
        # 평가셋에 빈칸 20건을 넣어 둔 것이 이 버그를 잡았다
        proc = [r for r in res if r.get('status') != 429]
        LANG = [('java', 'Java'), ('ts', 'TypeScript'), ('py', 'Python'),
                ('kt', 'Kotlin'), ('blank', '')]
        named_ok = named_n = 0
        for key, name in LANG:
            cell = [r for r in proc if (r['row'].get('language') or '') == name]
            hit = sum(1 for r in cell if r.get('status') == 200)
            if not cell:
                continue
            v['card.lang.%s' % key] = rate(hit, len(cell))
            v['card.lang.%s.n' % key] = '%d/%d' % (hit, len(cell))
            v['card.lang.%s.bar' % key] = bar(hit, len(cell))
            v['card.lang.%s.fail' % key] = '%d건' % (len(cell) - hit)
            if name:
                named_ok += hit
                named_n += len(cell)
        v['card.named'] = rate(named_ok, named_n)
        v['card.named.n'] = '%d/%d' % (named_ok, named_n)
        v['card.named.cnt'] = '%d건' % named_n

        ms_ok = sorted(r['ms'] for r in res if r.get('status') == 200)
        ms_q = sorted(r['ms'] for r in res if r.get('status') == 429)
        ms_f = sorted(r['ms'] for r in res if r.get('status') not in (200, 429))
        if ms_ok:
            v['card.ms.min'] = secs(ms_ok[0])
            v['card.ms.ok'] = secs(ms_ok[len(ms_ok) // 2])
        if ms_q:
            v['card.ms.quota'] = '%dms' % ms_q[len(ms_q) // 2]
        if ms_f:
            v['card.ms.fail'] = (secs(ms_f[0]) if ms_f[0] == ms_f[-1]
                                 else '%.1f~%.1f초' % (ms_f[0] / 1000.0, ms_f[-1] / 1000.0))
    except Exception:
        pass

    for f in sorted(glob.glob(os.path.join(RUNS, 'COGI_코드리뷰*.json')), key=os.path.getmtime):
        run = json.loads(io.open(f, encoding='utf-8').read())
        res = run['results']
        if len(res) < 5:                      # 연결 확인용 1~2건짜리는 버린다
            continue
        model = None
        for r in res:
            if r.get('error'):
                continue
            try:
                model = json.loads(r['body'])['data']['modelName']
                break
            except Exception:
                pass
        key = VENDOR_KEY.get(model)
        if not key:
            continue
        ok, n = scored(run, 'cogi_category')
        ms = sorted(r['ms'] for r in res if not r.get('error'))
        v[key + '.cat'] = rate(ok, n)
        v[key + '.cat.n'] = '%d/%d' % (ok, n)
        v[key + '.cat.bar'] = bar(ok, n)
        v[key + '.sec'] = '%.1f초' % (ms[len(ms) // 2] / 1000.0) if ms else '—'
    return v


TARGETS = [
    ('tld', 'projects/triplinker.html', triplinker),
    ('cogid', 'projects/cogi.html', cogi),
]


def main():
    dry = '--dry' in sys.argv
    for prefix, page, build in TARGETS:
        vals = build()
        p = os.path.join(SITE, page)
        html = io.open(p, encoding='utf-8').read()
        out, hit, miss = fill(html, prefix, vals)
        print('  %-6s %-28s %2d칸 채움%s' %
              (prefix, os.path.basename(page), hit,
               ('  (값 없음: %s)' % ', '.join(sorted(set(miss))[:6])) if miss else ''))
        if dry:
            for k in sorted(vals):
                print('        %-22s %s' % (k, vals[k]))
        elif out != html:
            io.open(p, 'w', encoding='utf-8', newline='').write(out)
    if dry:
        print('  --dry 라 파일은 안 건드렸다')
    return 0


if __name__ == '__main__':
    sys.exit(main())
