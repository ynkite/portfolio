# -*- coding: utf-8 -*-
"""쪽 하나에서 요소들의 실제 높이와 계산된 스타일을 본다.

사용 — python tools/_probe.py <쪽번호> <셀렉터> [셀렉터...]
"""
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfkit import CHROME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
page = int(sys.argv[1])
sels = sys.argv[2:] or ['.pgbody']

js = '''<script>addEventListener("load",function(){document.fonts.ready.then(function(){
var o=[],p=document.querySelectorAll(".page")[%d],sels=%s;
sels.forEach(function(s){
  var e=p.querySelector(s);
  if(!e){o.push(s+"  없음");return}
  var r=e.getBoundingClientRect(),c=getComputedStyle(e);
  o.push(s+"  h"+Math.round(r.height)+"  top"+Math.round(r.top)+
    "  display:"+c.display+"  min-height:"+c.minHeight+"  margin-top:"+c.marginTop+
    "  flex:"+c.flex);
});
document.title="PB"+JSON.stringify(o)})});</script>''' % (page - 1, json.dumps(sels))

tmp = os.path.join(ROOT, '_probe_tmp.html')
io.open(tmp, 'w', encoding='utf-8', newline='').write(
    io.open(os.path.join(ROOT, '_pdf.html'), encoding='utf-8').read().replace('</body>', js + '</body>'))
out = subprocess.run(
    [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
     '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_pb'),
     '--window-size=1123,794', '--virtual-time-budget=60000',
     '--dump-dom', 'file:///' + tmp.replace(os.sep, '/')],
    capture_output=True).stdout.decode('utf-8', 'replace')
os.remove(tmp)
m = re.search(r'<title>PB(\[.*?\])</title>', out, re.S)
print('p%02d' % page)
for x in json.loads(m.group(1) if m else '[]'):
    print('   ', x)
