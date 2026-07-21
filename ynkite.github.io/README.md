# 정상연 포트폴리오 — ynkite.github.io

하나의 내용, 다섯 가지 디자인의 정적 포트폴리오 사이트입니다.
빌드 도구 없이 순수 HTML/CSS/JS 단일 파일로 구성되어 어디서든 바로 동작합니다.

## 폴더 구성

```
ynkite.github.io/
├── index.html      ← 디자인 선택 페이지 (5개 미리보기)
├── magazine/       ① 매거진 — 잡지 커버 스타일
├── gallery/        ② 갤러리 — 미술관 전시 컨셉
├── bento/          ③ 벤토 — 워크스페이스 감성
├── poster/         ④ 포스터 — 스위스 타이포그래피
├── story/          ⑤ 스토리 — 스크롤 내러티브
├── Dockerfile
└── docker-compose.yml
```

## 1. GitHub Pages 배포

1. GitHub에서 `ynkite.github.io` 이름으로 저장소 생성 (반드시 본인 아이디.github.io)
2. 이 폴더의 내용 전체를 저장소에 push:
   ```bash
   git init
   git add .
   git commit -m "portfolio"
   git branch -M main
   git remote add origin https://github.com/ynkite/ynkite.github.io.git
   git push -u origin main
   ```
3. 몇 분 뒤 `https://ynkite.github.io` 접속 → 디자인 선택 페이지가 뜹니다.
4. **하나의 디자인만 대표로 쓰고 싶다면**: 마음에 드는 폴더의 `index.html`을 루트 `index.html`에 덮어쓰면 됩니다.
   ```bash
   cp magazine/index.html index.html   # 예: 매거진을 대표로
   ```

## 2. Docker로 상시 서버 돌리기 (남는 노트북 활용)

노트북에 Docker만 설치하면 됩니다.

```bash
# 이 폴더에서
docker compose up -d
# → http://localhost:8080 에서 확인
```

또는 compose 없이:

```bash
docker build -t portfolio .
docker run -d --name portfolio -p 8080:80 --restart unless-stopped portfolio
```

`--restart unless-stopped` 옵션 덕분에 노트북을 재부팅해도 자동으로 다시 뜹니다.

### 다른 기기(핸드폰 등)에서 접속하기

- 같은 와이파이: 노트북의 내부 IP 확인(`ipconfig` → IPv4) 후 `http://192.168.x.x:8080`
- 외부에서 접속: 공유기에서 8080 포트포워딩을 하거나, [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) / [Tailscale](https://tailscale.com) 사용을 추천합니다 (무료, 포트 개방 불필요).

## 3. 로컬에서 미리보기

Docker 없이도 폴더의 `index.html`을 브라우저로 열면 바로 보입니다.
(폰트는 CDN이라 인터넷 연결 필요)

## 수정 방법

- 각 디자인은 `폴더명/index.html` 파일 하나에 HTML/CSS/JS가 전부 들어 있습니다.
- 프로젝트 추가/문구 수정은 해당 index.html에서 텍스트만 고치면 됩니다.
- 공통 정보: 이메일 `j.sangyeon6@gmail.com`, GitHub `ynkite`, 블로그 `my-commit.tistory.com`
