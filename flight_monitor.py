#!/usr/bin/env python3
"""
Amadeus SDK를 활용한 항공 가격 모니터링
2025년 10월 4일-8일 직항 항공편 모니터링
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import pytz
import time
import logging

from amadeus import Client, ResponseError  # SDK import 추가

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AmadeusFlightMonitor:
    """Amadeus SDK 항공 모니터링"""
    
    def __init__(self):
        # 환경 변수에서 설정 로드
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not all([self.telegram_bot_token, self.telegram_chat_id]):
            raise ValueError("필수 환경 변수가 설정되지 않았습니다")
        
        self.bot = Bot(token=self.telegram_bot_token)
        
        # Amadeus SDK 클라이언트 초기화 (환경 변수 사용 추천)
        self.amadeus = Client(
            client_id=os.environ.get('AMADEUS_API_KEY'),
            client_secret=os.environ.get('AMADEUS_API_SECRET')
        )
        
        # 한국 시간대 설정
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 모니터링 설정
        self.origin = os.environ.get('ORIGIN', 'ICN')
        self.destination = os.environ.get('DESTINATION', 'HNL')
        self.departure_date = "2025-10-04"
        self.return_date = "2025-10-08"
        self.adults = 2
        self.max_price = 4000000  # 2인 총액 400만원
        self.direct_only = True  # 직항만
        
    def get_airline_name(self, carrier_code: str) -> str:
        """항공사 코드를 이름으로 변환"""
        # 기존 딕셔너리 유지
        
    def get_airline_booking_url(self, carrier_code: str) -> str:
        """항공사별 예약 사이트 URL"""
        # 기존 딕셔너리 유지
    
    def search_flights(self) -> Dict:
        """항공편 검색 - SDK 사용"""
        params = {
            'originLocationCode': self.origin,
            'destinationLocationCode': self.destination,
            'departureDate': self.departure_date,
            'returnDate': self.return_date,
            'adults': self.adults,
            'nonStop': self.direct_only,
            'currencyCode': 'KRW',
            'max': 50
        }
        
        try:
            kst_now = datetime.now(self.kst)
            logger.info(f"[{kst_now.strftime('%H:%M:%S')} KST] 항공편 검색 중...")
            response = self.amadeus.shopping.flight_offers_search.get(**params)
            offers = response.data
            logger.info(f"검색 성공! {len(offers)}개 항공편 발견")
            return {'data': offers, 'dictionaries': response.result.get('dictionaries', {})}
        except ResponseError as error:
            logger.error(f"검색 오류: {error}")
            return {}
        except Exception as e:
            logger.error(f"예기치 않은 오류: {e}")
            return {}
    
    def confirm_price(self, offer: Dict) -> Optional[Dict]:
        """Pricing SDK로 가격 확인 - 실패 시 원본 반환"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.amadeus.shopping.flight_offers.pricing.post(offer)
                return response.data['flightOffers'][0]
            except ResponseError as error:
                logger.warning(f"Pricing 오류 (시도 {attempt+1}): {error}")
            except Exception as e:
                logger.error(f"Pricing 예외 (시도 {attempt+1}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(5)
        
        logger.info("Pricing 실패 - Search 결과 사용")
        return offer
    
    # parse_flights(), format_duration, format_time, send_telegram_message, format_message, monitor_and_notify 등 기존 유지
    # parse_flights()에서 self.confirm_price(offer) 호출 시 SDK 버전으로 맞춤

async def main():
    # 기존 유지

if __name__ == "__main__":
    asyncio.run(main())
