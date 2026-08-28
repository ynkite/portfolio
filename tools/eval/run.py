# -*- coding: utf-8 -*-
"""평가셋을 대상 API에 돌리고 원본 응답을 남긴다.

실행과 채점을 나눈 이유 — 호출은 느리고 돈이 든다. 한 번 받아 둔 응답을
여러 채점 기준으로 다시 볼 수 있어야 실험을 여러 번 돌린다.

한 건이 여러 번 호출로 이뤄지는 경우가 있어 `steps` 로 짠다.
예 — TripLinker 는 여행 생성 → 입력폼 저장 → 경로 생성 세 번이라야 결과가 나온다.
앞 단계 응답에서 값을 뽑아(`capture`) 뒤 단계에 넘긴다.

사용
  python tools/eval/run.py tools/eval/experiments/cogi-card.json
  python tools/eval/run.py <설정> --limit 3      앞 3건만 (연결 확인용)
"""
import csv
import io
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, 'runs')

COOKIES = {}          # 로그인 응답의 Set-Cookie 를 담아 이후 요청에 붙인다


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """리다이렉트를 따라가지 않는다.

    토큰이 만료되면 서버가 302 로 로그인 페이지를 가리킨다. 그걸 따라가면
    HTML 이 200 으로 돌아와 실패가 성공으로 기록된다. 실제로 그렇게 43건이 오염됐다.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def load(path):
    return json.loads(io.open(path, encoding='utf-8').read())


def rows(path):
    with io.open(path, encoding='utf-8-sig', newline='') as fp:
        return list(csv.DictReader(fp))


def fill(obj, ctx):
    """{이름} 은 문맥 값으로, ${이름} 은 환경변수로 바꾼다."""
    if isinstance(obj, str):
        s = re.sub(r'\$\{(\w+)\}', lambda m: os.environ.get(m.group(1), ''), obj)
        m = re.fullmatch(r'\{(\w+)\}', s)          # 값 전체가 자리표시자면 타입을 살린다
        if m:
            v = ctx.get(m.group(1), '')
            if isinstance(v, str) and re.fullmatch(r'-?\d+', v):
                return int(v)
            return v
        return re.sub(r'\{(\w+)\}', lambda m: str(ctx.get(m.group(1), '')), s)
    if isinstance(obj, dict):
        return {k: fill(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fill(v, ctx) for v in obj]
    return obj


def dig(obj, path):
    cur = obj
    for part in path.split('.'):
        if cur is None:
            return None
        if isinstance(cur, list):
            if not part.isdigit() or int(part) >= len(cur):
                return None
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def multipart(fields, base_dir):
    """파일 첨부용 본문을 손으로 짠다. 외부 패키지를 안 쓰기 위해서다.

    값이 `@경로` 면 파일로 붙인다. 경로는 평가셋 파일이 있는 폴더 기준.
    """
    boundary = '----eval' + uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\n' % boundary).encode())
        s = str(v)
        if s.startswith('@'):
            p = s[1:]
            if not os.path.isabs(p):
                p = os.path.join(base_dir, p)
            name = os.path.basename(p)
            ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
            out.write(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                       % (k, name)).encode())
            out.write(('Content-Type: %s\r\n\r\n' % ctype).encode())
            out.write(io.open(p, 'rb').read())
            out.write(b'\r\n')
        else:
            out.write(('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode())
            out.write(s.encode('utf-8'))
            out.write(b'\r\n')
    out.write(('--%s--\r\n' % boundary).encode())
    return out.getvalue(), 'multipart/form-data; boundary=%s' % boundary


def call(cfg, step, ctx, base_dir):
    base = fill(cfg.get('base', ''), ctx)
    url = base + fill(step.get('path', ''), ctx) if step.get('path') else fill(step['url'], ctx)
    headers = fill(dict(cfg.get('headers', {})), ctx)
    headers.update(fill(dict(step.get('headers', {})), ctx))
    method = step.get('method', 'GET').upper()

    data = None
    if step.get('multipart'):
        data, ctype = multipart(fill(step['multipart'], ctx), base_dir)
        headers['Content-Type'] = ctype
    elif step.get('body') is not None:
        data = json.dumps(fill(step['body'], ctx), ensure_ascii=False).encode('utf-8')
        headers.setdefault('Content-Type', 'application/json; charset=utf-8')

    if COOKIES and 'Cookie' not in headers:
        headers['Cookie'] = '; '.join('%s=%s' % kv for kv in COOKIES.items())

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    try:
        with OPENER.open(req, timeout=step.get('timeout', cfg.get('timeout', 60))) as r:
            for raw in r.headers.get_all('Set-Cookie') or []:
                nv = raw.split(';', 1)[0]
                if '=' in nv:
                    k, v = nv.split('=', 1)
                    COOKIES[k.strip()] = v.strip()
            return {'status': r.status, 'ms': int((time.time() - t0) * 1000),
                    'body': r.read().decode('utf-8', 'replace'), 'error': None, 'url': url}
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'ms': int((time.time() - t0) * 1000),
                'body': e.read().decode('utf-8', 'replace'),
                'error': 'HTTP %d' % e.code, 'url': url}
    except Exception as e:
        return {'status': 0, 'ms': int((time.time() - t0) * 1000), 'body': '',
                'error': '%s: %s' % (type(e).__name__, e), 'url': url}


def sign_in(cfg, base_dir, quiet=False):
    """로그인은 평가셋 전체에 한 번만 한다. 100번 로그인할 이유가 없다.

    본문으로 토큰을 주면 `capture` 로 받아 헤더에 쓰고,
    쿠키로 주면 자동으로 담겨 이후 요청에 붙는다.
    """
    auth = cfg.get('auth')
    if not auth:
        return {}
    bare = dict(cfg)
    bare['headers'] = auth.get('headers', {})   # 토큰을 받기 전이니 전역 헤더는 뺀다
    r = call(bare, auth, {}, base_dir)
    if r['error']:
        raise SystemExit('로그인 실패 — %s  %s\n   %s'
                         % (r['error'], r['url'], r['body'][:200]))
    got = {}
    if auth.get('capture'):
        try:
            obj = json.loads(r['body'])
            for key, path in auth['capture'].items():
                got[key] = dig(obj, path)
        except Exception:
            pass
        missing = [k for k, v in got.items() if v in (None, '')]
        if missing:
            raise SystemExit('로그인 응답에서 %s 를 못 찾았다.\n   응답 %s'
                             % (','.join(missing), r['body'][:200]))
    if not got and not COOKIES:
        raise SystemExit('로그인은 됐는데 토큰도 쿠키도 없다.\n   응답 %s'
                         % r['body'][:200])
    if not quiet:
        print('  로그인 %s%s' % ('쿠키 %d개 ' % len(COOKIES) if COOKIES else '',
                              ' '.join('%s=****' % k for k in got)))
    return got


def steps_of(cfg):
    if cfg.get('steps'):
        return cfg['steps']
    return [{'url': cfg['url'], 'method': cfg.get('method', 'GET'),
             'body': cfg.get('body'), 'multipart': cfg.get('multipart'), 'score': True}]


def expired(r):
    """토큰이 죽었을 때의 모양. 302 는 로그인 페이지로 보내는 것이고 401 은 대놓고 거절이다."""
    return r['status'] in (301, 302, 303, 307, 308, 401)


def one(cfg, row, base_dir, auth_ctx=None):
    """한 건을 끝까지 돌린다. 채점 대상은 `score: true` 인 단계(없으면 마지막)."""
    ctx = dict(auth_ctx or {})
    ctx.update(row)
    steps = steps_of(cfg)
    trail, scored, total_ms = [], None, 0
    for i, st in enumerate(steps):
        r = call(cfg, st, ctx, base_dir)
        if expired(r) and cfg.get('auth'):
            # 긴 평가셋에서는 도중에 토큰이 만료된다. 다시 받아 그 단계만 재시도한다
            COOKIES.clear()
            fresh = sign_in(cfg, base_dir, quiet=True)
            ctx.update(fresh)
            r = call(cfg, st, ctx, base_dir)
        total_ms += r['ms']
        trail.append({'step': st.get('name', str(i)), 'status': r['status'],
                      'ms': r['ms'], 'error': r['error']})
        if r['error']:
            r['ms'] = total_ms
            r['trail'] = trail
            return r
        if st.get('capture'):
            try:
                obj = json.loads(r['body'])
                for key, path in st['capture'].items():
                    ctx[key] = dig(obj, path)
            except Exception:
                pass
            empty = [k for k in st['capture'] if ctx.get(k) in (None, '')]
            if empty:
                # 빈 값을 그대로 두면 /api/trips//... 같은 URL 이 만들어져
                # 엉뚱한 400 이 나고 원인을 못 찾는다. 여기서 끊는다
                r['error'] = '%s 를 못 받음 (%s 단계)' % (','.join(empty), st.get('name', str(i)))
                r['ms'] = total_ms
                r['trail'] = trail
                return r
        if st.get('score') or i == len(steps) - 1:
            scored = r
    scored['ms'] = total_ms if len(steps) > 1 else scored['ms']
    scored['trail'] = trail
    return scored


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cfg_path = os.path.abspath(sys.argv[1])
    cfg = load(cfg_path)
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 0

    set_path = cfg['set']
    if not os.path.isabs(set_path):
        set_path = os.path.join(HERE, set_path)
    base_dir = os.path.dirname(set_path)
    data = rows(set_path)
    if limit:
        data = data[:limit]
    repeat = cfg.get('repeat', 1)

    auth_ctx = sign_in(cfg, base_dir)

    out, n, total = [], 0, len(data) * repeat
    for row in data:
        for k in range(repeat):
            n += 1
            r = one(cfg, row, base_dir, auth_ctx)
            r['id'] = row.get('id', str(n))
            r['try'] = k + 1
            r['row'] = row
            out.append(r)
            sys.stdout.write('\r  %s %d/%d  %sms   ' %
                             ('ok ' if r['error'] is None else 'ERR', n, total, r['ms']))
            sys.stdout.flush()
    print()

    os.makedirs(RUNS, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    name = re.sub(r'[^\w.-]+', '_', cfg.get('name', os.path.basename(cfg_path)))
    path = os.path.join(RUNS, '%s-%s.json' % (name, stamp))
    io.open(path, 'w', encoding='utf-8', newline='').write(
        json.dumps({'config': cfg, 'ran_at': stamp, 'results': out},
                   ensure_ascii=False, indent=1))
    bad = sum(1 for r in out if r['error'])
    print('%d건 실행 / 실패 %d건 -> %s' % (len(out), bad, os.path.relpath(path, HERE)))
    if bad:
        first = next(r for r in out if r['error'])
        print('   첫 실패 — %s  %s' % (first['error'], first.get('url', '')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
