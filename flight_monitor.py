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
import pytz
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        airline_names = {
            # 한국 항공사
            'KE': '대한항공',
            'OZ': '아시아나항공',
            'LJ': '진에어',
            'TW': '티웨이',
            'ZE': '이스타항공',
            '7C': '제주항공',
            'BX': '에어부산',
            'RS': '에어서울',
            'YP': '에어프레미아',
            'RF': '에어로케이',
            # 미국 항공사
            'UA': '유나이티드',
            'DL': '델타',
            'AA': '아메리칸',
            'HA': '하와이안항공',
            'AS': '알래스카항공',
            # 아시아 항공사
            'JL': '일본항공(JAL)',
            'NH': '전일본공수(ANA)',
            'SQ': '싱가포르항공',
            'CX': '캐세이퍼시픽',
            'CI': '중화항공',
            'BR': '에바항공',
            'TG': '타이항공',
            'MH': '말레이시아항공',
            'PR': '필리핀항공',
            'VN': '베트남항공',
            # 기타
            'AC': '에어캐나다',
            'QF': '콴타스',
            'NZ': '에어뉴질랜드',
            'LH': '루프트한자',
            'AF': '에어프랑스',
            'BA': '영국항공',
            'EK': '에미레이트',
            'TK': '터키항공',
        }
        
        return airline_names.get(carrier_code, f'{carrier_code} 항공')
    
    def get_airline_booking_url(self, carrier_code: str) -> str:
        """항공사별 예약 사이트 URL"""
        urls = {
            'KE': 'https://www.koreanair.com',
            'OZ': 'https://flyasiana.com',
            'LJ': 'https://www.jinair.com',
            'TW': 'https://www.twayair.com',
            '7C': 'https://www.jejuair.net',
            'UA': 'https://www.united.com',
            'DL': 'https://www.delta.com',
            'AA': 'https://www.aa.com',
            'HA': 'https://www.hawaiianairlines.com',
            'JL': 'https://www.jal.co.jp',
            'NH': 'https://www.ana.co.jp',
        }
        return urls.get(carrier_code, 'https://www.google.com/flights')
    
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
            logger.info("Amadeus 인증 토큰 요청 중...")
            response = requests.post(token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 1799)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                logger.info("인증 성공!")
                return self.access_token
            else:
                logger.error(f"인증 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"토큰 요청 오류: {e}")
            return None
    
    def search_flights(self) -> Dict:
        """항공편 검색 - Amadeus API (가격 포함 요청)"""
        
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
            'max': 50,
        }
        
        try:
            kst_now = datetime.now(self.kst)
            logger.info(f"[{kst_now.strftime('%H:%M:%S')} KST] 항공편 검색 중...")
            response = requests.get(search_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                offers = data.get('data', [])
                logger.info(f"검색 성공! {len(offers)}개 항공편 발견")
                return {'data': offers, 'dictionaries': data.get('dictionaries', {})}
            else:
                logger.error(f"API 오류: {response.status_code} - {response.text[:200]}")
                return {}
                
        except Exception as e:
            logger.error(f"검색 오류: {e}")
            return {}
    
    def confirm_price(self, offer: Dict) -> Optional[Dict]:
        """Pricing API로 가격 확인 - 실패 시 원본 반환"""
        token = self.get_access_token()
        if not token:
            return offer  # 토큰 실패 시 원본 반환
        
        pricing_url = f"{self.base_url}/v2/shopping/flight-offers/pricing"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'data': {
                'type': 'flight-offers-pricing',
                'flightOffers': [offer]
            }
        }
        
        max_retries = 2  # 재시도 횟수 줄임
        for attempt in range(max_retries):
            try:
                response = requests.post(pricing_url, headers=headers, json=payload, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('data', {}).get('flightOffers', [offer])[0]
                elif response.status_code == 500:
                    # 500 에러는 Amadeus 서버 이슈일 가능성 높음
                    logger.warning(f"Pricing API 500 에러 (시도 {attempt+1}/{max_retries})")
                else:
                    logger.error(f"Pricing API 오류: {response.status_code}")
            except Exception as e:
                logger.error(f"Pricing 오류 (시도 {attempt+1}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2)
        
        # Pricing 실패 시 원본 offer 반환
        logger.info("Pricing API 실패 - Search 결과 사용")
        return offer
    
    def format_duration(self, duration: str) -> str:
        """ISO 8601 기간을 읽기 쉬운 형식으로 변환"""
        # PT13H30M -> 13시간 30분
        try:
            duration = duration.replace('PT', '')
            hours = 0
            minutes = 0
            
            if 'H' in duration:
                hours_part = duration.split('H')[0]
                hours = int(hours_part)
                duration = duration.split('H')[1]
            
            if 'M' in duration:
                minutes_part = duration.replace('M', '')
                minutes = int(minutes_part)
            
            return f"{hours}시간 {minutes}분" if minutes > 0 else f"{hours}시간"
        except:
            return duration
    
    def format_time(self, datetime_str: str) -> str:
        """시간 포맷팅"""
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime('%H:%M')
        except:
            return datetime_str
    
    def parse_flights(self, data: Dict) -> List[Dict]:
        """Amadeus API 응답 파싱 - 개선된 버전"""
        
        flights = []
        offers = data.get('data', [])
        dictionaries = data.get('dictionaries', {})
        carriers = dictionaries.get('carriers', {})
        aircraft = dictionaries.get('aircraft', {})
        
        try:
            for offer in offers:
                # 가격 확인 (Pricing API 시도, 실패 시 Search 결과 사용)
                confirmed_offer = self.confirm_price(offer)
                price_info = confirmed_offer.get('price', {})
                
                total_price = float(price_info.get('total', '0'))
                if total_price == 0:
                    logger.warning("가격 정보 없음 - 건너뜀")
                    continue
                
                per_person = total_price / self.adults
                
                # 1인당 200만원 초과 시 스킵
                if per_person > 2000000:
                    continue
                
                # 여정 정보
                itineraries = confirmed_offer.get('itineraries', [])
                if len(itineraries) < 2:
                    continue
                
                outbound = itineraries[0]
                inbound = itineraries[1]
                
                outbound_segments = outbound.get('segments', [])
                inbound_segments = inbound.get('segments', [])
                
                # 직항 체크
                if self.direct_only and (len(outbound_segments) > 1 or len(inbound_segments) > 1):
                    continue
                
                # 첫 세그먼트 정보
                out_seg = outbound_segments[0] if outbound_segments else {}
                in_seg = inbound_segments[0] if inbound_segments else {}
                
                # 항공사 정보
                out_carrier = out_seg.get('carrierCode', '')
                in_carrier = in_seg.get('carrierCode', '')
                
                flight_info = {
                    'carrier_code': out_carrier,
                    'airline': self.get_airline_name(out_carrier),
                    'price_per_person': per_person,
                    'price_total': total_price,
                    'currency': price_info.get('currency', 'KRW'),
                    'outbound': {
                        'departure': out_seg.get('departure', {}).get('at', ''),
                        'arrival': out_seg.get('arrival', {}).get('at', ''),
                        'flight_number': f"{out_carrier}{out_seg.get('number', '')}",
                        'duration': self.format_duration(outbound.get('duration', ''))
                    },
                    'inbound': {
                        'departure': in_seg.get('departure', {}).get('at', ''),
                        'arrival': in_seg.get('arrival', {}).get('at', ''),
                        'flight_number': f"{in_carrier}{in_seg.get('number', '')}",
                        'duration': self.format_duration(inbound.get('duration', ''))
                    },
                    'booking_url': self.get_airline_booking_url(out_carrier)
                }
                
                flights.append(flight_info)
            
            # 가격순 정렬
            flights.sort(key=lambda x: x['price_total'])
            logger.info(f"조건 충족 항공편: {len(flights)}개 (1인당 200만원 이하 직항)")
        
        except Exception as e:
            logger.error(f"파싱 오류: {e}", exc_info=True)
        
        return flights
    
    async def send_telegram_message(self, message: str) -> bool:
        """텔레그램 메시지 전송"""
        try:
            await self.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            logger.info("텔레그램 알림 전송 성공")
            return True
        except TelegramError as e:
            logger.error(f"텔레그램 전송 실패: {e}")
            return False
    
    def format_message(self, flights: List[Dict]) -> str:
        """텔레그램 메시지 포맷팅 - 개선된 버전"""
        kst_now = datetime.now(self.kst)
        current_time = kst_now.strftime('%Y-%m-%d %H:%M')
        
        if not flights:
            return (
                f"✈️ <b>항공편 모니터링</b>\n"
                f"📅 {self.departure_date} ~ {self.return_date}\n"
                f"🛫 {self.origin} → {self.destination}\n"
                f"👥 {self.adults}인 / 💺 직항\n"
                f"🔍 검색 시간: {current_time}\n\n"
                f"❌ 1인당 200만원 이하 직항 항공편이 없습니다.\n"
                f"💡 다음 검색: 30분 후"
            )
        
        message = (
            f"🎉 <b>조건 충족 항공편 발견!</b>\n"
            f"📅 {self.departure_date} ~ {self.return_date}\n"
            f"🛫 {self.origin} → {self.destination}\n"
            f"👥 {self.adults}인 / 💺 직항만\n"
            f"🔍 검색: {current_time}\n"
            f"{'='*30}\n\n\n"
        )
        
        for i, flight in enumerate(flights[:5], 1):  # 상위 5개만 표시
            message += (
                f"<b>{i}. {flight['airline']}</b>\n"
                f"💰 1인: {int(flight['price_per_person']):,}원\n"
                f"💰 총액: {int(flight['price_total']):,}원\n"
                f"🛫 가는편: {flight['outbound']['flight_number']}\n"
                f"   {self.format_time(flight['outbound']['departure'])} → "
                f"{self.format_time(flight['outbound']['arrival'])} "
                f"({flight['outbound']['duration']})\n"
                f"🛬 오는편: {flight['inbound']['flight_number']}\n"
                f"   {self.format_time(flight['inbound']['departure'])} → "
                f"{self.format_time(flight['inbound']['arrival'])} "
                f"({flight['inbound']['duration']})\n"
                f"🔗 <a href='{flight['booking_url']}'>예약하기</a>\n\n"
            )
        
        if len(flights) > 5:
            message += f"... 외 {len(flights)-5}개 항공편 더 있음\n"
        
        return message
    
    async def monitor_and_notify(self):
        """메인 모니터링 함수"""
        kst_now = datetime.now(self.kst)
        logger.info(f"모니터링 시작: {kst_now.strftime('%Y-%m-%d %H:%M:%S')} KST")
        
        data = self.search_flights()
        if not data:
            logger.error("항공편 검색 실패")
            return
        
        flights = self.parse_flights(data)
        
        # 조건 충족 항공편이 있을 때만 알림
        if flights:
            message = self.format_message(flights)
            await self.send_telegram_message(message)
        else:
            logger.info("조건 충족 항공편 없음")
            # 디버그용: 조건 미달 시 상태 알림 (선택사항)
            # message = self.format_message([])
            # await self.send_telegram_message(message)

async def main():
    """메인 실행 함수"""
    try:
        monitor = AmadeusFlightMonitor()
        
        # 단일 실행 모드
        await monitor.monitor_and_notify()
        
        # 반복 실행 모드 (주석 해제하여 사용)
        # while True:
        #     await monitor.monitor_and_notify()
        #     logger.info("30분 후 다시 검색...")
        #     await asyncio.sleep(1800)  # 30분
        
    except KeyboardInterrupt:
        logger.info("모니터링 중단")
    except Exception as e:
        logger.error(f"실행 오류: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
