"""한글 본문 블록만 뽑아 번호를 붙인다. script/style/code 안은 제외.
단위 = '한글을 직접 담고 있고, 자식 엘리먼트에는 한글 텍스트가 없는' 가장 안쪽 엘리먼트의 innerHTML.
그래야 문장 리듬을 볼 수 있는 덩어리로 나가고, 되넣을 때 태그가 보존된다."""
import json, re, sys
from html.parser import HTMLParser

KO = re.compile(r"[가-힣]")
VOID = {"br", "img", "meta", "link", "input", "hr", "source"}
SKIP = {"script", "style", "code"}


class Blocks(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.lines = [0]
        for line in src.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))
        self.stack = []          # [tag, inner_start, own_ko, child_ko]
        self.out = []            # (start, end, inner_html)
        self.skip_depth = 0

    def off(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        if tag in SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        end = self.src.index(">", self.off()) + 1
        self.stack.append([tag, end, False, False])

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth or not self.stack:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                frame = self.stack.pop(i)
                del self.stack[i:]
                break
        else:
            return
        t, start, own_ko, child_ko = frame
        if own_ko and not child_ko:
            self.out.append((start, self.off(), self.src[start:self.off()]))
        if (own_ko or child_ko) and self.stack:
            self.stack[-1][3] = True

    def handle_data(self, data):
        if self.skip_depth or not self.stack or not KO.search(data):
            return
        self.stack[-1][2] = True


def run(paths):
    units = []
    for p in paths:
        src = open(p, encoding="utf-8").read()
        body = src.index("<body")
        b = Blocks(src[body:])
        b.feed(src[body:])
        for start, end, inner in b.out:
            text = inner.strip()
            if not KO.search(text):
                continue
            units.append({"file": p, "start": body + start, "end": body + end, "html": inner})
    return units


if __name__ == "__main__":
    out, paths = sys.argv[1], sys.argv[2:]
    units = run(paths)
    json.dump(units, open(out + "/units.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(out + "/01_input.txt", "w", encoding="utf-8") as f:
        for i, u in enumerate(units, 1):
            f.write("[%d] %s\n" % (i, u["html"].strip()))
    total = sum(len(u["html"]) for u in units)
    print("units=%d chars=%d" % (len(units), total))
