# tidyupAV — CLAUDE.md

이 프로젝트는 **LLM Wiki 패턴**으로 운영됩니다.
Claude는 단순 질문 응답에 그치지 않고, 아래의 wiki/ 디렉토리에 구조화된 마크다운 파일을 지속적으로 유지합니다.

---

## 프로젝트 개요

AV 파일 정리 자동화 도구 (Windows, Python 기반)

| 파일 | 역할 |
|---|---|
| `organizer.py` | tkinter GUI — 품번별/배우별 파일 이동 |
| `crawler/javdb.py` | JavDB 크롤러 |
| `crawler/db.py` | SQLite DB 관리 |
| `crawler/models.py` | 데이터 모델 |
| `wiki/` | LLM Wiki 지식베이스 |

---

## LLM Wiki 운영 규칙

### 아키텍처 3계층

```
Raw Sources (웹페이지, 사용자 입력)
       ↓
   Wiki (wiki/*.md — LLM이 생성·유지)
       ↓
  Schema (이 CLAUDE.md — 구조와 워크플로우 정의)
```

### 핵심 파일

- `wiki/index.md` — 카테고리별 콘텐츠 목록
- `wiki/log.md` — 시간순 변경 로그 (append-only)

### 주요 오퍼레이션

**Ingest** — 새 정보가 들어오면:
1. 관련 wiki 페이지 업데이트 or 신규 생성
2. `wiki/index.md`에 항목 추가
3. `wiki/log.md`에 타임스탬프 기록

**Query** — 질문에 답할 때:
1. 관련 wiki 페이지 먼저 참조
2. 답변이 새로운 인사이트라면 wiki에 기록

**Lint** — 주기적으로:
1. 오래된 정보, 모순, 고아 페이지 식별
2. 사용자에게 보고

### Wiki 페이지 작성 원칙

- 파일명: `wiki/topic-name.md` (영어 소문자, 하이픈)
- 각 페이지 상단에 `# 제목` + 한 줄 설명
- 관련 페이지는 `[[링크]]` 형식으로 상호 참조
- 불확실한 정보는 `> ⚠️ 미확인` 인용구로 표시

---

## 개발 규칙

- Python 3.10+, 표준 라이브러리 우선
- DB: SQLite (추가 설치 불필요)
- HTTP: `cloudscraper` (Cloudflare 우회)
- HTML 파싱: `beautifulsoup4`
- GUI: `tkinter` (내장)
- 크롤링 시 요청 간격 최소 1~2초 유지
- 모든 크롤링 결과는 DB에 캐싱 (동일 데이터 재요청 금지)
