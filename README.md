# tidyupAV

AV 파일 정리 자동화 도구 (Windows / Python)

---

## 실행 방법

`run.bat` 을 더블클릭하거나, 터미널에서:

```
python organizer.py
```

---

## 파일 정리 GUI 사용법

1. `run.bat` 실행
2. **소스 폴더** — 정리할 파일이 들어있는 폴더 선택
3. **대상 폴더** — 정리 결과를 저장할 폴더 선택
4. **정렬 방식** 선택:
   - `title` (작품별): 품번마다 개별 폴더 생성 → `MIDV-707/`, `PRED-571/`
   - `prefix` (품번분류별): 제작사 prefix별 폴더 생성 → `MIDV/`, `PRED/`
5. **파일 유형** 체크: 영상 / 이미지 / 자막
6. **미리보기** 버튼으로 이동 결과 확인
7. **실행** 버튼으로 파일 이동 (또는 복사)

> 품번을 인식하지 못한 파일은 `_미분류/` 폴더로 이동됩니다.

---

## 인식 가능한 파일명 패턴

| 파일명 예시 | 인식 결과 |
|---|---|
| `midv-707.mp4` | MIDV-707 |
| `[MIDV-707]_제목_1080p.mp4` | MIDV-707 |
| `(HD)PRED-571_4K_uncen.mkv` | PRED-571 |
| `CAWD707_fhd_1080p.mp4` | CAWD-707 |
| `SSNI_357_1080p_x264.mp4` | SSNI-357 |
| `FC2-PPV-1234567.mp4` | FC2-PPV-1234567 |
| `200GANA-2789.mp4` | 200GANA-2789 |
| `1pon-123456_01.mp4` | 1PON-123456 |
| `3dsvr-0967.mp4` | 3DSVR-0967 |
| `T28-557.mp4` | T28-557 |
| `some_text_MIRD-220_garbage.mp4` | MIRD-220 |
| `midv sadfsadfsdaff 707.mp4` | MIDV-707 ← 퍼지 매칭 |
| `MIDV 랜덤텍스트 00707 1080p.mp4` | MIDV-707 ← 퍼지 매칭 |

---

## 초기 설정

**패키지 설치**
```
pip install cloudscraper beautifulsoup4 psycopg2-binary python-dotenv
```


## 폴더 구조

```
tidyupAV/
├── run.bat            ← GUI 실행 배치파일
├── organizer.py       ← 파일 정리 GUI
├── data/
│   └── javdb.db       ← 크롤링 결과 데이터 수집중
└── wiki/              ← 프로젝트 지식베이스
```
