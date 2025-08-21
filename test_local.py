#!/usr/bin/env python3
"""
로컬 테스트용 스크립트
GitHub Actions 없이 로컬에서 테스트할 때 사용
"""

import os
import asyncio
from dotenv import load_dotenv
from flight_monitor import RapidAPIFlightMonitor

# .env 파일 로드
load_dotenv()

# 환경 변수 확인
def check_env_vars():
    """필수 환경 변수 확인"""
    required = ['RAPIDAPI_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing = []
    
    for var in required:
        if not os.getenv(var):
            missing.append(var)
    
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

async def test_telegram():
    """텔레그램 연결 테스트"""
    from telegram import Bot
    
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

async def test_rapidapi():
    """RapidAPI 연결 테스트"""
    import requests
    
    print("\n🌐 RapidAPI 연결 테스트...")
    headers = {
        "X-RapidAPI-Key": os.getenv('RAPIDAPI_KEY'),
        "X-RapidAPI-Host": "sky-scanner3.p.rapidapi.com"
    }
    
    # 간단한 API 테스트 (시장 정보 조회)
    url = "https://sky-scanner3.p.rapidapi.com/get-config"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ RapidAPI 연결 성공!")
            return True
        else:
            print(f"❌ RapidAPI 오류: {response.status_code}")
            print(f"   응답: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ RapidAPI 연결 실패: {e}")
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
    rapid_ok = await test_rapidapi()
    telegram_ok = await test_telegram()
    
    if not (rapid_ok and telegram_ok):
        print("\n⚠️ 일부 테스트 실패. 위 오류를 확인하세요.")
        return
    
    print("\n" + "=" * 50)
    print("모든 테스트 통과! 실제 항공편 검색을 시작합니다...")
    print("=" * 50)
    
    # 3. 실제 모니터링 실행
    try:
        monitor = RapidAPIFlightMonitor()
        await monitor.monitor_and_notify()
        print("\n✅ 모니터링 완료! 텔레그램을 확인하세요.")
    except Exception as e:
        print(f"\n❌ 모니터링 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n시작하려면 Enter를 누르세요 (취소: Ctrl+C)")
    input()
    asyncio.run(main())
