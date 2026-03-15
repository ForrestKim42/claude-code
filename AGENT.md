# Instagram 광고 릴스 성과 추적 시스템

이 브랜치는 **광고 릴스 성과 데이터 수집 및 자동화 리포트**만을 위한 브랜치입니다.

---

## 구조

```
ad-reel-tracker/
├── config.yaml                        # 추적 대상 릴스 URL · 수집 설정
├── main.py                            # 실행 진입점
├── requirements.txt
├── data/
│   └── reels.db                       # SQLite 시계열 저장소
├── reports/
│   └── dashboard.html                 # 생성된 HTML 대시보드
├── tracker/
│   ├── apify_scraper.py               # Apify 수집기 (기본)
│   ├── instaloader_scraper.py         # Instaloader 수집기 (무료 대안)
│   └── storage.py                     # DB 저장/조회 로직
├── reporter/
│   └── html_report.py                 # HTML 대시보드 생성기
└── .github/workflows/
    └── track-reels.yml                # 6시간마다 자동 수집·리포트
```

---

## 추적 대상 릴스

| 계정 | URL |
|------|-----|
| 신소윤 @thinxoyoon | https://www.instagram.com/reel/DV0fRYczORi/ |
| 하 나 @ha_n_a0.6 | https://www.instagram.com/reel/DV0hL9HEb2H/ |
| 서윤 @xeo.yuunny | https://www.instagram.com/reel/DV0iKVxk3Ew/ |
| 에스더 @esther_ffff | https://www.instagram.com/reel/DV0i7t-Ehq0/ |
| 지여닝 @caiime_pretty | https://www.instagram.com/reel/DV0hBoMkkjp/ |

---

## 수집 지표

| 지표 | 설명 |
|------|------|
| Views | 순수 조회수 (중복 제거) |
| Plays | 총 재생 횟수 (반복 포함) |
| Likes | 좋아요 수 |
| Comments | 댓글 수 |
| Engagement Rate | (likes + comments) / views × 100 |

> Instagram은 어떤 서드파티에도 **노출수(Impressions)** 를 제공하지 않습니다.

---

## 실행 방법

```bash
cd ad-reel-tracker
pip install -r requirements.txt

# 수집 + 대시보드 한 번에
APIFY_API_TOKEN=<토큰> python main.py --all --apify

# 수집만
APIFY_API_TOKEN=<토큰> python main.py --collect --apify

# 대시보드만 (기존 DB 데이터 기반)
python main.py --report
```

대시보드 파일: `reports/dashboard.html` → 브라우저에서 바로 열기 가능

---

## 자동화 (GitHub Actions)

레포지토리 Settings → Secrets → **`APIFY_API_TOKEN`** 추가 시
`.github/workflows/track-reels.yml` 이 6시간마다 자동 실행됩니다.

- 수집 결과는 `data/reels.db` 에 누적 저장
- 최신 `reports/dashboard.html` 은 자동 커밋됨
- 실행 로그 및 dashboard.html 은 Actions Artifacts 에서 다운로드 가능

---

## 수집기 선택 기준

| 수집기 | 비용 | 안정성 | 비고 |
|--------|------|--------|------|
| **Apify** (`apify/instagram-scraper`) | ~$0.002/릴스 | ⭐⭐⭐⭐ | 기본 사용 권장 |
| **Instaloader** | 무료 | ⭐⭐⭐ | GraphQL 변경 시 깨질 수 있음 |
