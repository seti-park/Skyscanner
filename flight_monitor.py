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
import time  # 재시도 대기용

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
        
        # OAuth2 토큰
        self.access_token = None
        self.token_expires_at = None
        
        # 한국 시간대 설정
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 모니터링 설정 (YAML env 읽기)
        self.origin = os.environ.get('ORIGIN', 'ICN')
        self.destination = os.environ.get('DESTINATION', 'HNL')
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
        """Pricing API로 가격 확인 - 재시도 추가"""
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
        
        for attempt in range(3):  # 3회 재시도
            try:
                response = requests.post(pricing_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('data', {}).get('flightOffers', [None])[0]
                else:
                    print(f"Pricing API 오류 (재시도 {attempt+1}): {response.status_code} - {response.text[:200]}")
            except Exception as e:
                print(f"Pricing 재시도 {attempt+1} 오류: {e}")
            time.sleep(5)  # 5초 대기
        
        return None
    
    def parse_flights(self, data: Dict) -> List[Dict]:
        """Amadeus API 응답 파싱 - Pricing 실패 시 fallback 강화"""
        
        flights = []
        offers = data.get('data', [])
        dictionaries = data.get('dictionaries', {})
        carriers = dictionaries.get('carriers', {})
        
        try:
            for offer in offers:
                # Pricing 시도
                confirmed_offer = self.confirm_price(offer)
                
                if confirmed_offer:
                    price_info = confirmed_offer.get('price', {})
                    is_pricing_success = True
                else:
                    print("Pricing 실패: Search 가격으로 fallback")
                    price_info = offer.get('price', {})
                    is_pricing_success = False
                
                total_price = float(price_info.get('total', '0'))
                per_person = total_price / self.adults
                
                # 여정 정보 (직항 체크 등, 기존 로직 가정)
                itineraries = offer.get('itineraries', [])
                if len(itineraries) < 2:
                    continue
                
                outbound_itinerary = itineraries[0]
                return_itinerary = itineraries[1]
                
                outbound_segments = outbound_itinerary.get('segments', [])
                return_segments = return_itinerary.get('segments', [])
                
                if self.direct_only and (len(outbound_segments) > 1 or len(return_segments) > 1):
                    continue
                
                # 항공사 정보
                outbound_carrier = outbound_segments[0].get('carrierCode', '') if outbound_segments else ''
                airline = self.get_airline_name(outbound_carrier)
                
                # 조건 체크: 1인당 200만원 이하
                if per_person <= 2000000:
                    flight_info = {
                        'carrier_code': outbound_carrier,
                        'airline': airline,
                        'price_per_person': per_person if is_pricing_success else '추정 가격 (Pricing 실패로 확인 불가)',
                        'price_total': total_price,
                        'currency': price_info.get('currency', 'KRW'),
                        # ... (기존 다른 정보: outbound, inbound 등 추가 가능)
                    }
                    flights.append(flight_info)
            
            flights.sort(key=lambda x: x['price_total'])
            print(f"조건 충족 항공편: {len(flights)}개 (200만원 이하 직항)")
        
        except Exception as e:
            print(f"파싱 오류: {e}")
        
        return flights
    
    # ... (기존 메서드: get_airline_name, get_airline_booking_url, format_duration, format_time, send_telegram_message 등 유지)
    
    def format_message(self, flights: List[Dict]) -> str:
        """텔레그램 메시지 포맷팅 - 가격 없어도 항공사 출력"""
        kst_now = datetime.now(self.kst)
        current_time = kst_now.strftime('%Y-%m-%d %H:%M')
        
        if not flights:
            return (
                f"✈️ <b>항공편 모니터링 (Amadeus)</b>\n"
                f"📅 {self.departure_date} ~ {self.return_date}\n"
                f"🛫 {self.origin} → {self.destination}\n"
                f"👥 {self.adults}인 / 💺 직항\n"
                f"🔍 검색 시간: {current_time}\n\n"
                f"❌ 200만원 이하 직항 항공편이 없습니다.\n"
                f"다음 검색: 30분 후"
            )
        
        message = (
            f"✈️ <b>항공편 발견! ({len(flights)}개)</b>\n"
            f"📅 {self.departure_date} ~ {self.return_date}\n"
            f"🛫 {self.origin} → {self.destination}\n"
            f"👥 {self.adults}인 / 💺 직항만\n"
            f"🔍 검색: {current_time}\n"
            f"{'='*30}\n\n"
            f"<b>조건 충족 항공사 목록 (200만원 이하):</b>\n"
        )
        
        for i, flight in enumerate(flights, 1):
            price_str = f"{int(flight['price_per_person'])} KRW" if isinstance(flight['price_per_person'], (int, float)) else flight['price_per_person']
            message += f"{i}. {flight['airline']} ({flight['carrier_code']}): 1인당 {price_str}\n"
        
        # 예약 링크 등 추가 (기존 로직)
        message += "\n공식 사이트에서 확인하세요."
        
        return message
    
    async def monitor_and_notify(self):
        """메인 모니터링 함수"""
        kst_now = datetime.now(self.kst)
        
        data = self.search_flights()
        if not data:
            return
        
        flights = self.parse_flights(data)
        
        if flights:  # 조건 충족 시 알림
            message = self.format_message(flights)
            await self.send_telegram_message(message)

async def main():
    try:
        monitor = AmadeusFlightMonitor()
        await monitor.monitor_and_notify()
    except Exception as e:
        print(f"실행 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())
