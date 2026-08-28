# -*- coding: utf-8 -*-
"""설정에 적힌 모델이 지금도 벤더에 살아 있는지 확인한다.

폴백은 1차가 죽었을 때를 위한 것인데, 2차가 조용히 죽어 있으면 아무 소용이 없다.
평소에는 1차가 잘 도니까 아무도 모른다. 그래서 따로 찔러 본다.
"""
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

PROPS = r'E:\daewooproject\trip-linker\src\main\resources\application.properties'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runs', 'vendor_health.json')
UA = {'User-Agent': 'triplinker-eval/1.0'}      # 기본 UA 는 Cloudflare 가 막는다

cfg = io.open(PROPS, encoding='utf-8', errors='replace').read()


def prop(k, d=''):
    m = re.search(re.escape(k) + r'=(.*)', cfg)
    return m.group(1).strip() if m else d


def post(url, headers, body, timeout=40):
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                 headers=dict(headers, **UA))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()[:200].decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode('utf-8', 'replace')
    except Exception as e:
        return 0, '%s: %s' % (type(e).__name__, e)


checks = []

# 1차 — Claude (코드에서 메인으로 바뀌어 있다)
m = prop('spring.ai.anthropic.chat.options.model')
s, b = post('https://api.anthropic.com/v1/messages',
            {'x-api-key': prop('spring.ai.anthropic.api-key'),
             'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
            {'model': m, 'max_tokens': 8, 'messages': [{'role': 'user', 'content': 'hi'}]})
checks.append({'단계': '1차', '벤더': 'Claude', '모델': m, 'status': s,
               '상태': '정상' if 200 <= s < 300 else '실패', '응답': b[:120]})

# 2차 — Groq (설정상 ai.primary=groq 이지만 코드에서 폴백으로 내려갔다)
m = prop('spring.ai.openai.chat.options.model')
s, b = post(prop('spring.ai.openai.base-url') + '/v1/chat/completions',
            {'Authorization': 'Bearer ' + prop('spring.ai.openai.api-key'),
             'Content-Type': 'application/json'},
            {'model': m, 'max_tokens': 8, 'messages': [{'role': 'user', 'content': 'hi'}]})
checks.append({'단계': '2차', '벤더': 'Groq', '모델': m, 'status': s,
               '상태': '정상' if 200 <= s < 300 else '실패', '응답': b[:120]})

# 3차 — Gemini (챗봇 쪽 폴백)
m = prop('spring.ai.google.genai.chat.options.model')
url = ('https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s'
       % (m, prop('spring.ai.google.genai.api-key')))
s, b = post(url, {'Content-Type': 'application/json'},
            {'contents': [{'parts': [{'text': 'hi'}]}]})
checks.append({'단계': '3차', '벤더': 'Gemini', '모델': m, 'status': s,
               '상태': '정상' if 200 <= s < 300 else '실패', '응답': b[:120]})

io.open(OUT, 'w', encoding='utf-8', newline='').write(
    json.dumps(checks, ensure_ascii=False, indent=1))

for c in checks:
    print('%-4s %-8s %-28s HTTP %-4s %s' % (c['단계'], c['벤더'], c['모델'], c['status'], c['상태']))
    if c['상태'] != '정상':
        print('       %s' % re.sub(r'\s+', ' ', c['응답'])[:110])
print('-> %s' % OUT)
