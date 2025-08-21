#!/usr/bin/env python3
"""
Amadeus API를 활용한 항공 가격 모니터링
2025년 10월 3일-8일 직항 항공편 모니터링
무료 티어: 월 2,000회 요청 (30분마다 실행 가능)
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
from telegram import Bot
from telegram.error import TelegramError

class AmadeusFlightMonitor:
    """Amadeus API 항공 모니터링"""

    def __init__(self):
        # 환경 변수에서 설정 로드
        self.amadeus_api_key = os.environ.get('AMADEUS_API_KEY')
        self.amadeus_api_secret = os.environ.get('AMADEUS_API_SECRET')
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not all([self.amadeus_api_key, self.amadeus_api_secret, 
                   self.telegram_bot_token, self.telegram_chat_id]):
            raise ValueError("필수 환경 변수가 설정되지 않았습니다")
        
        self.bot = Bot(token=self.telegram_bot_token)
        
        # Amadeus API 엔드포인트 (프로덕션)
        self.base_url = "https://api.amadeus.com"
        # 테스트 환경을 원한다면: "https://test.api.amadeus.com"
        
        # OAuth2 토큰
        self.access_token = None
        self.token_expires_at = None
        
        # 모니터링 설정
        self.origin = "ICN"  # 인천공항
        self.destination = "HNL"  # 하와이 호놀룰루
        self.departure_date = "2025-10-04"
        self.return_date = "2025-10-08"
        self.adults = 2
        self.max_price = 1500000  # 150만원 (2인 총액)
        self.direct_only = True  # 직항만

    def get_access_token(self) -> str:
        """Amadeus OAuth2 토큰 획득"""
        # ... (이하 동일, 들여쓰기 유지)
        # 모든 메서드는 들여쓰기가 필요합니다!

    # 이하 모든 함수는 들여쓰기 후 붙여넣기!

    # ... 모든 본문 함수코드 동일하게 들여쓰기!

# main 함수
async def main():
    """메인 실행 함수"""
    try:
        monitor = AmadeusFlightMonitor()
        await monitor.monitor_and_notify()
    except Exception as e:
        print(f"실행 오류: {e}")
        import traceback
        traceback.print_exc()
        # 오류 발생 시 텔레그램 알림
        if os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID'):
            bot = Bot(token=os.environ.get('TELEGRAM_BOT_TOKEN'))
            await bot.send_message(
                chat_id=os.environ.get('TELEGRAM_CHAT_ID'),
                text=f"❌ 모니터링 오류 발생\n{str(e)[:200]}"
            )

if __name__ == "__main__":
    asyncio.run(main())
