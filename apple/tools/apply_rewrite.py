"""윤문 결과(03_rewrite.md)를 실제 HTML 파일에 되넣는다.

되넣기 전에 줄 단위로 세 가지를 검사하고, 하나라도 어긋나면 그 줄은 건너뛴다.
  1) HTML 태그 시퀀스가 원문과 완전히 동일한가
  2) 숫자 토큰이 원문과 같은가 (수치 변형 차단)
  3) <code> 안의 내용이 그대로인가 (메서드·상수명 보존)
"""
import json, os, re, sys

WS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_workspace", "2026-07-30-001")
ROOT = r"C:\Users\USER\Downloads\ynkite.github.io\redesign2\apple"

TAG = re.compile(r"<[^>]+>")
NUM = re.compile(r"\d+")
CODE = re.compile(r"<code>(.*?)</code>", re.S)


def norm(s):
    return " ".join(s.split())


def tags(s):
    return [t.lower().replace(" /", "/") for t in TAG.findall(s)]


def load_rewrite(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\[(\d+)\]\s(.*)$", line.rstrip("\n"))
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def main(write):
    prose = json.load(open(os.path.join(WS, "prose.json"), encoding="utf-8"))
    rw = load_rewrite(os.path.join(WS, "03_rewrite.md"))
    files, edits, skipped = {}, [], []

    for u in prose:
        i = u["id"]
        new = rw.get(i)
        if new is None:
            continue
        old_norm = norm(u["html"])
        new = norm(new)
        if new == old_norm:
            continue

        why = None
        if tags(old_norm) != tags(new):
            why = "태그 시퀀스 불일치"
        elif sorted(NUM.findall(old_norm)) != sorted(NUM.findall(new)):
            why = "숫자 토큰 불일치"
        elif [norm(c) for c in CODE.findall(old_norm)] != [norm(c) for c in CODE.findall(new)]:
            why = "<code> 내용 불일치"
        if why:
            skipped.append((i, why, new[:60]))
            continue

        f = u["file"]
        if f not in files:
            files[f] = open(os.path.join(ROOT, f), encoding="utf-8").read()
        src = files[f]
        # 파일에 있는 원문(줄바꿈·들여쓰기 포함) 그대로 찾는다
        target = u["html"]
        n = src.count(target)
        if n != 1:
            # 공백만 다른 경우가 있어 정규화 형태로 한 번 더 시도
            alt = old_norm
            n2 = src.count(alt)
            if n2 == 1:
                target, n = alt, 1
            else:
                skipped.append((i, "본문에서 %d곳 발견(이후 편집으로 변경됨)" % n, new[:60]))
                continue
        files[f] = src.replace(target, new, 1)
        edits.append((i, f, old_norm, new))

    print("적용 대상 %d줄 / 건너뜀 %d줄" % (len(edits), len(skipped)))
    if skipped:
        print("\n-- 건너뜀")
        for i, why, s in skipped:
            print("   [%3d] %-32s %s" % (i, why, s))
    print("\n-- 적용 예시 (앞 12건)")
    for i, f, o, n in edits[:12]:
        print("   [%3d] %s" % (i, f))
        print("        전: %s" % o[:150])
        print("        후: %s" % n[:150])

    if write:
        for f, s in files.items():
            open(os.path.join(ROOT, f), "w", encoding="utf-8", newline="").write(s)
        print("\n%d개 파일 기록: %s" % (len(files), ", ".join(files)))
    else:
        print("\n(dry-run — 기록하지 않음)")


if __name__ == "__main__":
    main(write="--write" in sys.argv)
