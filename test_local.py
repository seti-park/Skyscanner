#!/usr/bin/env python3
"""
로컬 테스트용 스크립트
GitHub Actions 없이 로컬에서 테스트할 때 사용
"""

import os
import asyncio
import requests
from dotenv import load_dotenv
from telegram import Bot
from flight_monitor import AmadeusFlightMonitor


# .env 파일 로드
load_dotenv()


def check_env_vars() -> bool:
    """필수 환경 변수 확인"""
    required = ['AMADEUS_API_KEY', 'AMADEUS_API_SECRET', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print("❌ 다음 환경 변수가 설정되지 않았습니다:")
        for var in missing:
            print(f"   - {var}")
        print("\n💡 해결 방법:")
        print("1. .env.example을 .env로 복사")
        print("2. .env 파일을 열어 값 입력")
        print("3. 다시 실행")
        return False
    print("✅ 환경 변수 확인 완료")
    return True


async def test_telegram() -> bool:
    """텔레그램 연결 테스트"""
    print("\n📱 텔레그램 연결 테스트...")
    try:
        bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        await bot.send_message(
            chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            text="🔧 테스트 메시지: 항공 가격 모니터링 봇이 정상 작동합니다!"
        )
        print("✅ 텔레그램 메시지 전송 성공!")
        return True
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")
        return False


async def test_amadeus() -> bool:
    """Amadeus API 연결 테스트"""
    print("\n🌐 Amadeus API 연결 테스트...")

    # 환경에 맞는 토큰 URL 선택
    amadeus_env = os.getenv('AMADEUS_ENV', 'test').lower()
    base_url = "https://api.amadeus.com" if amadeus_env in ("prod", "production", "live") else "https://test.api.amadeus.com"
    token_url = f"{base_url}/v1/security/oauth2/token"

    data = {
        'grant_type': 'client_credentials',
        'client_id': os.getenv('AMADEUS_API_KEY'),
        'client_secret': os.getenv('AMADEUS_API_SECRET')
    }

    try:
        response = requests.post(token_url, data=data, timeout=10)
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Amadeus API 인증 성공!")
            print(f"   토큰 유효시간: {token_data.get('expires_in', 0)}초")
            return True
        else:
            print(f"❌ Amadeus API 인증 실패: {response.status_code}")
            print(f"   응답: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Amadeus API 연결 실패: {e}")
        return False


async def main():
    """메인 테스트 함수"""
    print("=" * 50)
    print("🚀 항공 가격 모니터링 로컬 테스트")
    print("=" * 50)

    # 1. 환경 변수 확인
    if not check_env_vars():
        return

    # 2. API 연결 테스트
    amadeus_ok = await test_amadeus()
    telegram_ok = await test_telegram()

    if not (amadeus_ok and telegram_ok):
        print("\n⚠️ 일부 테스트 실패. 위 오류를 확인하세요.")
        return

    print("\n" + "=" * 50)
    print("모든 테스트 통과! 실제 항공편 검색을 시작합니다...")
    print("=" * 50)

    # 3. 실제 모니터링 실행
    try:
        monitor = AmadeusFlightMonitor()
        await monitor.monitor_and_notify()
        print("\n✅ 모니터링 완료! 텔레그램을 확인하세요.")
    except Exception as e:
        print(f"\n❌ 모니터링 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
