#!/usr/bin/env python3
"""
Amadeus API를 활용한 항공 가격 모니터링
2025년 10월 4일-8일 직항 항공편 모니터링
프로덕션 API 사용: 실제 데이터
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import pytz  # 한국 시간대 처리용

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
        
        # Amadeus API 엔드포인트 (프로덕션 환경으로 변경)
        self.base_url = "https://api.amadeus.com"
        
        # OAuth2 토큰
        self.access_token = None
        self.token_expires_at = None
        
        # 한국 시간대 설정
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 모니터링 설정 (인천-호놀룰루, 10월 4일-8일)
        self.origin = "ICN"  # 인천공항
        self.destination = "HNL"  # 호놀룰루 (하와이)
        self.departure_date = "2025-10-04"
        self.return_date = "2025-10-08"
        self.adults = 2
        self.max_price = 4000000  # 2인 총액 400만원 (1인당 200만원 이하)
        self.direct_only = True  # 직항만
        
    def get_access_token(self) -> Optional[str]:
        """Amadeus OAuth2 토큰 획득"""
        
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        token_url = f"{self.base_url}/v1/security/oauth2/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.amadeus_api_key,
            'client_secret': self.amadeus_api_secret
        }
        
        try:
            print("Amadeus 인증 토큰 요청 중...")
            response = requests.post(token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 1799)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                print("인증 성공!")
                return self.access_token
            else:
                print(f"인증 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"토큰 요청 오류: {e}")
            return None
    
    def search_flights(self) -> Dict:
        """항공편 검색 - Amadeus API"""
        
        token = self.get_access_token()
        if not token:
            return {}
        
        search_url = f"{self.base_url}/v2/shopping/flight-offers"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'originLocationCode': self.origin,
            'destinationLocationCode': self.destination,
            'departureDate': self.departure_date,
            'returnDate': self.return_date,
            'adults': self.adults,
            'nonStop': 'true' if self.direct_only else 'false',
            'currencyCode': 'KRW',
            'max': 50
        }
        
        try:
            kst_now = datetime.now(self.kst)
            print(f"\n[{kst_now.strftime('%H:%M:%S')} KST] 항공편 검색 중...")
            response = requests.get(search_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                offers = data.get('data', [])
                print(f"검색 성공! {len(offers)}개 항공편 발견")
                return {'data': offers, 'dictionaries': data.get('dictionaries', {})}
            else:
                print(f"API 오류: {response.status_code} - {response.text[:200]}")
                return {}
                
        except Exception as e:
            print(f"검색 오류: {e}")
            return {}
    
    def confirm_price(self, offer: Dict) -> Optional[Dict]:
        """Pricing API로 가격 확인 - 정확성 향상"""
        token = self.get_access_token()
        if not token:
            return None
        
        pricing_url = f"{self.base_url}/v2/shopping/flight-offers/pricing"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'data': {
                'type': 'flight-offers-pricing',
                'flightOffers': [offer]
            }
        }
        
        try:
            response = requests.post(pricing_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('flightOffers', [None])[0]
            else:
                print(f"Pricing API 오류: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            print(f"Pricing 오류: {e}")
            return None
    
    def parse_flights(self, data: Dict) -> List[Dict]:
        """Amadeus API 응답 파싱 - Pricing 확인 추가"""
        
        flights = []
        offers = data.get('data', [])
        dictionaries = data.get('dictionaries', {})
        carriers = dictionaries.get('carriers', {})
        
        try:
            for offer in offers:
                # Pricing API로 확인 (중요: 데이터 정확성 up)
                confirmed_offer = self.confirm_price(offer)
                if not confirmed_offer:
                    continue
                
                # 가격 정보 (확인된 가격 사용)
                price_info = confirmed_offer.get('price', {})
                total_price = float(price_info.get('total', '0'))
                
                if total_price > self.max_price:
                    continue
                
                # 여정 정보 등 (기존 로직 유지, 생략)
                # ... (parse_flights의 나머지 코드 동일, confirmed_offer로 대체)
                # flight_info 생성
                
                flights.append(flight_info)
            
            flights.sort(key=lambda x: x['price_total'])
            print(f"조건 충족 항공편: {len(flights)}개 (200만원 이하 직항)")
            
        except Exception as e:
            print(f"파싱 오류: {e}")
        
        return flights
    
    # 나머지 메서드 (format_duration, send_telegram_message, format_time, get_airline_booking_url 등)는 당신 코드와 동일. 
    # get_airline_booking_url: KE URL 포맷 수정 (departure-date=2025-10-04 등 실제 사이트 맞춤)
    
    async def monitor_and_notify(self):
        """메인 모니터링 함수"""
        kst_now = datetime.now(self.kst)
        
        data = self.search_flights()
        if not data:
            # 오류 시 Telegram 알림 (조건 미달 시 알림 안 보내기)
            return
        
        flights = self.parse_flights(data)
        
        if flights:  # 조건 충족 시만 알림
            message = self.format_message(flights)
            await self.send_telegram_message(message)

# 메인 실행 (Actions용 1회 실행)
async def main():
    try:
        monitor = AmadeusFlightMonitor()
        await monitor.monitor_and_notify()
    except Exception as e:
        print(f"실행 오류: {e}")
        # Telegram 오류 알림 (기존)

if __name__ == "__main__":
    asyncio.run(main())
