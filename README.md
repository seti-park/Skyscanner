# ✈️ 항공 가격 자동 모니터링 (GitHub Actions + Telegram)

2025년 10월 3일-8일 직항 항공편을 30분마다 자동으로 모니터링하고 텔레그램으로 알림을 받는 시스템입니다.

## 🎯 모니터링 조건
- **날짜**: 2025년 10월 3일 출발 - 10월 8일 도착
- **인원**: 2명
- **가격**: 150만원 이하
- **항공편**: 직항만
- **체크 주기**: 30분마다 자동 실행

## 🚀 빠른 시작 가이드

### 1단계: 저장소 Fork 및 Clone

```bash
# 이 저장소를 Fork한 후
git clone https://github.com/YOUR_USERNAME/flight-monitor.git
cd flight-monitor
```

### 2단계: RapidAPI 키 발급

1. [RapidAPI](https://rapidapi.com) 가입
2. [Skyscanner API](https://rapidapi.com/3b-data-3b-data-default/api/sky-scanner3) 구독
   - Basic Plan (무료) 선택 가능
   - 월 100회 요청 무료 (30분마다 = 하루 48회 = 월 1,440회 필요)
   - Pro Plan ($10/월) 추천: 월 10,000회 요청
3. API Key 복사

### 3단계: 텔레그램 봇 생성

1. 텔레그램에서 [@BotFather](https://t.me/BotFather) 검색
2. 다음 명령어 실행:
```
/newbot
봇 이름 입력: Flight Price Monitor
봇 username 입력: your_flight_monitor_bot
```
3. 생성된 봇 토큰 저장

4. **Chat ID 확인**:
   - 생성한 봇에게 아무 메시지 전송
   - 브라우저에서 접속: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - `"chat":{"id":123456789}` 에서 숫자 복사

### 4단계: GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

다음 3개의 시크릿 추가:

| Name | Value |
|------|-------|
| `RAPIDAPI_KEY` | RapidAPI에서 복사한 키 |
| `TELEGRAM_BOT_TOKEN` | BotFather가 준 토큰 |
| `TELEGRAM_CHAT_ID` | 위에서 확인한 Chat ID |

### 5단계: GitHub Actions 활성화

1. Actions 탭 클릭
2. "I understand my workflows, go ahead and enable them" 클릭
3. 왼쪽 메뉴에서 "Flight Price Monitor" 선택
4. "Run workflow" 버튼으로 수동 테스트

## 📁 파일 구조

```
flight-monitor/
├── .github/
│   └── workflows/
│       └── flight-monitor.yml  # GitHub Actions 워크플로우
├── flight_monitor.py           # 메인 모니터링 스크립트
├── requirements.txt            # Python 패키지 목록
└── README.md                  # 이 파일
```

## 🔧 커스터마이징

### 노선 변경

`flight_monitor.py` 파일에서 수정:

```python
# 기본 설정
self.origin = "ICN"  # 인천
self.destination = "NRT"  # 도쿄 나리타

# 다른 공항 예시
self.origin = "ICN"  # 인천
self.destination = "BKK"  # 방콕

# 또는
self.origin = "GMP"  # 김포
self.destination = "HND"  # 하네다
```

### 주요 공항 코드

| 한국 | 일본 | 동남아 | 중국 |
|------|------|--------|------|
| ICN (인천) | NRT (나리타) | BKK (방콕) | PEK (베이징) |
| GMP (김포) | HND (하네다) | SIN (싱가포르) | PVG (상하이) |
| PUS (부산) | KIX (오사카) | KUL (쿠알라룸푸르) | HKG (홍콩) |
| CJU (제주) | FUK (후쿠오카) | DPS (발리) | TPE (타이베이) |

### 가격 임계값 변경

```python
self.max_price = 1500000  # 150만원
# 변경 예시
self.max_price = 2000000  # 200만원
```

### 실행 주기 변경

`.github/workflows/flight-monitor.yml` 에서:

```yaml
schedule:
  - cron: '*/30 * * * *'  # 30분마다
  # 변경 예시:
  # - cron: '0 */1 * * *'  # 1시간마다
  # - cron: '0 6,12,18 * * *'  # 하루 3번 (6시, 12시, 18시)
```

## 📊 모니터링 결과 예시

텔레그램으로 받게 될 메시지:

```
✈️ 항공편 발견! (3개)
📅 2025-10-03 ~ 2025-10-08
🛫 ICN → NRT
👥 2인 / 💺 직항만
🔍 검색: 2025-01-20 14:30
==============================

1. 대한항공
💰 총 1,450,000원 (1인 725,000원)
🛫 가는편: 09:20 → 11:45 (2시간 25분)
🛬 오는편: 13:00 → 15:30 (2시간 30분)

2. 아시아나항공
💰 총 1,480,000원 (1인 740,000원)
🛫 가는편: 14:10 → 16:35 (2시간 25분)
🛬 오는편: 17:20 → 19:50 (2시간 30분)
```

## ⚠️ 주의사항

### GitHub Actions 제한
- **Public 저장소**: 월 2,000분 무료
- **Private 저장소**: 월 2,000분 무료 (Free 계정)
- 30분마다 실행 = 하루 48회 × 1분 = 월 1,440분 사용
- 여유있게 사용 가능

### RapidAPI 제한
- **Basic (무료)**: 월 100회 - 부족함 ⚠️
- **Pro ($10/월)**: 월 10,000회 - 충분함 ✅
- **Ultra ($50/월)**: 월 100,000회

### 트러블슈팅

1. **"API rate limit exceeded"** 오류
   - RapidAPI 요청 한도 초과
   - Pro 플랜 업그레이드 필요

2. **텔레그램 메시지 안 옴**
   - Chat ID 확인
   - 봇과 대화 시작했는지 확인
   - GitHub Secrets 설정 확인

3. **Actions 실행 안 됨**
   - Actions 활성화 확인
   - workflow 파일 문법 확인
   - 저장소 Settings → Actions 권한 확인

## 📈 개선 아이디어

- [ ] 여러 노선 동시 모니터링
- [ ] 가격 변동 히스토리 저장
- [ ] 가격 하락 시만 알림
- [ ] 웹 대시보드 추가
- [ ] 항공사별 필터링
- [ ] 좌석 등급 선택 옵션

## 📝 라이선스

MIT License

## 🤝 기여

Pull Request 환영합니다!

## 📞 문의

문제가 있으면 Issue를 열어주세요.
