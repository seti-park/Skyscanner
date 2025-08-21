# 🚀 Amadeus API 무료 설정 가이드

## 📌 왜 Amadeus API인가?

### 장점

- ✅ **완전 무료**: 월 2,000회 요청 (30분마다 실행 가능)
- ✅ **신뢰성**: 전 세계 항공사 직접 연동
- ✅ **풍부한 데이터**: 실시간 가격, 좌석 정보, 터미널 정보
- ✅ **한국어/원화 지원**: KRW 가격 직접 제공
- ✅ **직항 필터링**: nonStop 파라미터로 간단하게

### 비교

|API        |월 비용  |무료 한도     |30분마다 실행|
|-----------|------|----------|--------|
|**Amadeus**|**무료**|**2,000회**|**가능** ✅|
|Kiwi.com   |$29   |500회      |불가능 ❌   |
|Skyscanner |파트너만  |-         |-       |

## 🎯 Amadeus API 가입 방법 (5분 소요)

### Step 1: 회원 가입

1. **[Amadeus for Developers](https://developers.amadeus.com)** 접속
1. 우측 상단 **“Register”** 클릭
1. 정보 입력:
- First Name: 이름
- Last Name: 성
- Email: 이메일
- Password: 비밀번호
- Country: South Korea
1. 이메일 인증

### Step 2: 앱 생성 및 API 키 발급

1. 로그인 후 **“My Self-Service Workspace”** 클릭
1. **“Create new app”** 클릭
1. 앱 정보 입력:
- App name: `Flight Monitor` (원하는 이름)
- Description: `Flight price monitoring`
1. **“Create”** 클릭

### Step 3: API 키 확인

생성 완료 후 바로 표시되는:

- **API Key**: `VGxxxxxxxxxxxxxxxxxxxxx` (32자)
- **API Secret**: `Hxxxxxxxxxxxxx` (16자)

⚠️ **중요**: 이 페이지를 벗어나면 Secret을 다시 볼 수 없으니 반드시 복사해두세요!

## 📝 GitHub Secrets 설정

### GitHub 저장소에서:

1. **Settings** → **Secrets and variables** → **Actions**
1. **New repository secret** 클릭
1. 다음 4개 시크릿 추가:

|Name                |Value          |설명                |
|--------------------|---------------|------------------|
|`AMADEUS_API_KEY`   |VGxxxxx…       |Amadeus API Key   |
|`AMADEUS_API_SECRET`|Hxxxxx…        |Amadeus API Secret|
|`TELEGRAM_BOT_TOKEN`|7012345678:AAH…|텔레그램 봇 토큰         |
|`TELEGRAM_CHAT_ID`  |123456789      |텔레그램 채팅 ID        |

## 🧪 로컬 테스트

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
AMADEUS_API_KEY=VGxxxxxxxxxxxxxxxxxxxxx
AMADEUS_API_SECRET=Hxxxxxxxxxxxxx
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### 2. 패키지 설치

```bash
pip install requests python-telegram-bot python-dotenv
```

### 3. 테스트 실행

```bash
python test_local.py
```

### 예상 출력:

```
✅ 환경 변수 확인 완료
🌐 Amadeus API 연결 테스트...
✅ Amadeus API 인증 성공!
   토큰 유효시간: 1799초
📱 텔레그램 연결 테스트...
✅ 텔레그램 메시지 전송 성공!
```

## 🔍 모니터링 대상 변경

### 노선 변경

`flight_monitor.py`에서:

```python
# 기본값 (인천 → 도쿄)
self.origin = "ICN"
self.destination = "NRT"

# 다른 예시
self.origin = "ICN"  # 인천
self.destination = "BKK"  # 방콕

self.origin = "GMP"  # 김포
self.destination = "HND"  # 하네다
```

### 날짜 변경

```python
self.departure_date = "2025-10-03"  # YYYY-MM-DD 형식
self.return_date = "2025-10-08"
```

### 가격 한도 변경

```python
self.max_price = 1500000  # 150만원 (2인 총액)
# 변경 예시
self.max_price = 2000000  # 200만원
```

## 📊 API 사용량 관리

### 현재 설정

- **실행 주기**: 30분마다 (하루 48회)
- **월 사용량**: 48 × 30 = 1,440회
- **무료 한도**: 2,000회
- **여유분**: 560회 (28%)

### 사용량 확인

1. [Amadeus 대시보드](https://developers.amadeus.com) 로그인
1. **“My Self-Service Workspace”**
1. 앱 선택 → **“Analytics”** 탭
1. 일별/월별 사용량 확인

## ⚙️ 고급 설정

### 테스트/프로덕션 환경

```python
# flight_monitor.py에서

# 테스트 환경 (기본값, 무료)
self.base_url = "https://test.api.amadeus.com"

# 프로덕션 환경 (유료 플랜 필요)
self.base_url = "https://api.amadeus.com"
```

### 추가 검색 옵션

```python
# 경유 허용
self.direct_only = False

# 클래스 지정
params['travelClass'] = 'BUSINESS'  # ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST

# 항공사 지정
params['includedAirlineCodes'] = 'KE,OZ'  # 대한항공, 아시아나만
```

## 🚨 트러블슈팅

### 1. “Invalid client” 오류

- API Key와 Secret이 정확한지 확인
- 앞뒤 공백 제거

### 2. “Rate limit exceeded” 오류

- 월 2,000회 초과
- 다음 달까지 대기 또는 실행 주기 조정

### 3. “No flights found” 결과

- 날짜가 너무 가까운 경우 (최소 3일 전 검색 권장)
- 노선에 직항이 없는 경우

### 4. 토큰 만료 오류

- 토큰은 30분마다 자동 갱신됨
- 코드에 이미 처리되어 있음

## 💡 팁

### 최적 검색 시간

- 항공사는 주로 화요일 오후에 가격 조정
- 주말보다 평일이 더 저렴한 경향

### API 한도 절약

- 중요 시간대만 체크:

```yaml
# .github/workflows/flight-monitor.yml
schedule:
  # 하루 6번만 (오전 6시, 9시, 12시, 3시, 6시, 9시)
  - cron: '0 6,9,12,15,18,21 * * *'
```

## 📈 확장 아이디어

1. **다중 노선 모니터링**
- 여러 도시 동시 체크
- 노선별 다른 가격 한도
1. **가격 히스토리**
- GitHub Actions artifacts 활용
- 가격 추이 그래프
1. **스마트 알림**
- 가격 하락시만 알림
- 특정 항공사 우선 알림

## 🎉 완료!

이제 무료로 항공 가격을 30분마다 모니터링할 수 있습니다!

- 월 비용: **0원**
- API 한도: **충분** (2,000회)
- 신뢰성: **높음** (Amadeus 직접 연동)
