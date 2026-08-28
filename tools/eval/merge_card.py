# -*- coding: utf-8 -*-
"""COGI 카드 생성 평가셋 100건을 두 번에 나눠 돌린 결과를 하나로 합친다.

왜 나눠 돌리나
  이 서비스는 요금제 일일 한도를 코드로 지킨다. MAX 플랜이 하루 70건이라
  100건을 한 번에 밀어 넣으면 71건째부터 HTTP 429 가 나온다. 한도는 버그가
  아니므로, 한도를 늘리는 대신 남은 문항을 다음 날 돌려 100건을 채운다.

무엇을 다시 돌리지 않나
  이미 200 으로 답을 받은 문항은 다시 돌리지 않는다. 같은 문항을 또 부르면
  모델 호출만 늘고 값은 달라질 수 있다. 답을 받지 못한 문항만 채운다.

  python tools/eval/merge_card.py            합쳐서 새 실행 파일로 쓴다
  python tools/eval/merge_card.py --dry      합친 결과만 보여 준다

합친 파일은 `runs/` 에서 가장 최신이 되므로 publish.py · publish_delta.py ·
trend.py 가 자동으로 이 값을 쓴다.
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, 'runs')

BASE = 'COGI_카드_생성_구조화_출력-20260825-233142.json'   # 100건을 처음 돌린 실행
NL = chr(10)


def load(name):
    return json.loads(io.open(os.path.join(RUNS, name), encoding='utf-8').read())


def newest_rest():
    """남은 문항만 돌린 실행 중 가장 최신 것."""
    c = glob.glob(os.path.join(RUNS, 'COGI_카드_생성_구조화_출력*남은*.json'))
    c += glob.glob(os.path.join(RUNS, '*남은_32건*.json'))
    c = [p for p in set(c) if os.path.basename(p) != BASE]
    if not c:
        return None
    return os.path.basename(sorted(c, key=os.path.getmtime)[-1])


def main():
    base = load(BASE)
    rest_name = newest_rest()
    if rest_name is None:
        print('남은 문항을 돌린 실행이 없다. 먼저 아래를 실행한다.')
        print('  python tools/eval/run.py tools/eval/experiments/cogi-card-rest.json')
        return 1
    rest = load(rest_name)
    print('  기준 실행 %s — %d건' % (BASE, len(base['results'])))
    print('  추가 실행 %s — %d건' % (rest_name, len(rest['results'])))

    # 답을 받은 것만 덮어쓴다. 새 실행에서도 실패하면 원래 실패 기록을 남긴다
    by_id = {r['id']: r for r in base['results']}
    filled = kept = 0
    for r in rest['results']:
        old = by_id.get(r['id'])
        if old is None:
            continue
        if old.get('status') == 200:
            kept += 1                      # 이미 검증된 문항은 손대지 않는다
            continue
        if r.get('status') == 200:
            by_id[r['id']] = r
            filled += 1
    print('  채운 문항 %d건 · 이미 검증돼 그대로 둔 문항 %d건' % (filled, kept))

    merged = dict(base)
    merged['results'] = [by_id[r['id']] for r in base['results']]
    merged['ran_at'] = base['ran_at'] + '+' + rest['ran_at']
    merged['merged_from'] = [BASE, rest_name]
    merged['merge_note'] = ('요금제 일일 한도(70건)로 한 번에 100건을 돌릴 수 없어 '
                            '두 날에 나눠 돌렸다. 이미 답을 받은 문항은 다시 부르지 않았다.')

    st = {}
    for r in merged['results']:
        st[r.get('status')] = st.get(r.get('status'), 0) + 1
    print('  합친 결과 %d건 — %s' % (len(merged['results']), st))

    if '--dry' in sys.argv:
        return 0

    stamp = rest['ran_at']
    out = os.path.join(RUNS, 'COGI_카드_생성_구조화_출력-%s-merged.json' % stamp)
    io.open(out, 'w', encoding='utf-8', newline='').write(
        json.dumps(merged, ensure_ascii=False, indent=1) + NL)
    print('  %s' % os.path.basename(out))
    print('  이어서: python tools/eval/publish_delta.py && python tools/eval/publish.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
