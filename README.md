# ✈️ 항공 가격 자동 모니터링 (GitHub Actions + Telegram)

**완전 무료**로 2025년 10월 3일-8일 직항 항공편을 30분마다 자동 모니터링하고 텔레그램으로 알림을 받는 시스템입니다.

## 🎯 모니터링 조건

- **날짜**: 2025년 10월 3일 출발 - 10월 8일 도착
- **인원**: 2명
- **가격**: 150만원 이하
- **항공편**: 직항만
- **체크 주기**: 30분마다 자동 실행
- **비용**: **완전 무료** (Amadeus API 무료 티어 사용)

## 🚀 빠른 시작 가이드 (10분 소요)

### 1단계: 저장소 Fork 및 Clone

```bash
# 이 저장소를 Fork한 후
git clone https://github.com/YOUR_USERNAME/flight-monitor.git
cd flight-monitor
```

### 2단계: Amadeus API 키 발급 (무료)

1. [Amadeus for Developers](https://developers.amadeus.com) 가입
1. “My Self-Service Workspace” → “Create new app”
1. API Key와 API Secret 복사 (중요: Secret은 한 번만 표시됨)
1. **무료 티어**: 월 2,000회 요청 (30분마다 실행 가능!)

### 3단계: 텔레그램 봇 생성

1. 텔레그램에서 [@BotFather](https://t.me/BotFather) 검색
1. 다음 명령어 실행:

```
/newbot
봇 이름 입력: Flight Price Monitor
봇 username 입력: your_flight_monitor_bot
```

1. 생성된 봇 토큰 저장
1. **Chat ID 확인**:
- 생성한 봇에게 아무 메시지 전송
- 브라우저에서 접속: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
- `"chat":{"id":123456789}` 에서 숫자 복사

### 4단계: GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

다음 4개의 시크릿 추가:

|Name                |Value                    |
|--------------------|-------------------------|
|`AMADEUS_API_KEY`   |Amadeus에서 발급받은 API Key   |
|`AMADEUS_API_SECRET`|Amadeus에서 발급받은 API Secret|
|`TELEGRAM_BOT_TOKEN`|BotFather가 준 토큰          |
|`TELEGRAM_CHAT_ID`  |위에서 확인한 Chat ID          |

### 5단계: GitHub Actions 활성화

1. Actions 탭 클릭
1. “I understand my workflows, go ahead and enable them” 클릭
1. 왼쪽 메뉴에서 “Flight Price Monitor” 선택
1. “Run workflow” 버튼으로 수동 테스트

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

|한국      |일본        |동남아         |중국        |
|--------|----------|------------|----------|
|ICN (인천)|NRT (나리타) |BKK (방콕)    |PEK (베이징) |
|GMP (김포)|HND (하네다) |SIN (싱가포르)  |PVG (상하이) |
|PUS (부산)|KIX (오사카) |KUL (쿠알라룸푸르)|HKG (홍콩)  |
|CJU (제주)|FUK (후쿠오카)|DPS (발리)    |TPE (타이베이)|

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
📅 2025년 10월 3일 ~ 10월 8일
🛫 ICN → NRT
👥 2인 / 💺 직항만
🔍 검색: 2025-01-20 14:30
==============================

1. 대한항공
💰 총 1,450,000원 (1인 725,000원)
🛫 가는편: 09:20 → 11:45 (2시간 25분)
   편명: KE001 (T2)
🛬 오는편: 13:00 → 15:30 (2시간 30분)
   편명: KE002 (T1)
💺 예약 가능: 9석
🎫 클래스: 이코노미

2. 아시아나항공
💰 총 1,480,000원 (1인 740,000원)
🛫 가는편: 14:10 → 16:35 (2시간 25분)
   편명: OZ101
🛬 오는편: 17:20 → 19:50 (2시간 30분)
   편명: OZ102
💺 예약 가능: 5석
🎫 클래스: 이코노미

==============================
📊 Amadeus API 무료 티어
월 2,000회 중 사용 중
```

## ⚠️ 주의사항

### API 제한

- **Amadeus 무료 티어**: 월 2,000회 요청
- **30분마다 실행**: 하루 48회 × 30일 = 월 1,440회
- **여유 한도**: 560회 (테스트 및 수동 실행용)

### GitHub Actions 제한

- **Public 저장소**: 월 2,000분 무료
- **Private 저장소**: 월 2,000분 무료 (Free 계정)
- 30분마다 실행 = 하루 48회 × 1분 = 월 1,440분 사용
- 여유있게 사용 가능

### 트러블슈팅

1. **“Invalid client”** 오류
- API Key와 Secret 확인
- 앞뒤 공백 제거
- Secrets 설정 확인
1. **텔레그램 메시지 안 옴**
- Chat ID 확인
- 봇과 대화 시작했는지 확인
- GitHub Secrets 설정 확인
1. **“No flights found”** 결과
- 너무 임박한 날짜는 결과 없을 수 있음
- 직항이 없는 노선일 수 있음
1. **Actions 실행 안 됨**
- Actions 활성화 확인
- workflow 파일 문법 확인
- 저장소 Settings → Actions 권한 확인

## 💰 비용 분석

|항목            |비용    |설명            |
|--------------|------|--------------|
|Amadeus API   |**무료**|월 2,000회 무료 제공|
|GitHub Actions|**무료**|월 2,000분 무료 제공|
|텔레그램          |**무료**|메시지 전송 무료     |
|**총 비용**      |**0원**|완전 무료!        |

## 📈 개선 아이디어

- [ ] 여러 노선 동시 모니터링
- [ ] 가격 변동 히스토리 저장
- [ ] 가격 하락 시만 알림
- [ ] 웹 대시보드 추가
- [ ] 항공사별 필터링
- [ ] 좌석 등급 선택 옵션
- [ ] 경유 1회 허용 옵션
- [ ] 주말/평일 가격 비교

## 🎉 핵심 장점

- **완전 무료**: API 비용 0원
- **충분한 한도**: 월 2,000회 (30분마다 실행 가능)
- **신뢰성 높음**: Amadeus 공식 API (전 세계 항공사 직접 연동)
- **풍부한 정보**: 좌석 수, 터미널, 클래스 정보 포함
- **자동화**: GitHub Actions로 24시간 자동 모니터링

## 📝 라이선스

MIT License

## 🤝 기여

Pull Request 환영합니다!

## 📞 문의

문제가 있으면 Issue를 열어주세요.
