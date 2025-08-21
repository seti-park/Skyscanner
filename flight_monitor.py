#!/usr/bin/env python3
"""
RapidAPI Skyscanner를 활용한 항공 가격 모니터링
2025년 10월 3일-8일 직항 항공편 모니터링
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from telegram import Bot
from telegram.error import TelegramError

class RapidAPIFlightMonitor:
    """RapidAPI Skyscanner 항공 모니터링"""
    
    def __init__(self):
        # 환경 변수에서 설정 로드
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY')
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not all([self.rapidapi_key, self.telegram_bot_token, self.telegram_chat_id]):
            raise ValueError("필수 환경 변수가 설정되지 않았습니다")
        
        self.bot = Bot(token=self.telegram_bot_token)
        
        # RapidAPI 엔드포인트
        self.search_url = "https://sky-scanner3.p.rapidapi.com/flights/search-roundtrip"
        self.headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": "sky-scanner3.p.rapidapi.com"
        }
        
        # 모니터링 설정
        self.origin = "ICN"  # 인천공항
        self.destination = "NRT"  # 도쿄 나리타 (필요시 변경)
        self.departure_date = "2025-10-03"
        self.return_date = "2025-10-08"
        self.adults = 2
        self.max_price = 1500000  # 150만원
        self.direct_only = True  # 직항만
        
    def search_flights(self) -> Dict:
        """항공편 검색"""
        
        params = {
            "fromEntityId": self.origin,
            "toEntityId": self.destination,
            "departDate": self.departure_date,
            "returnDate": self.return_date,
            "adults": str(self.adults),
            "cabinClass": "economy",
            "currency": "KRW",
            "market": "KR",
            "locale": "ko-KR"
        }
        
        try:
            print(f"[{datetime.now()}] 항공편 검색 중...")
            print(f"노선: {self.origin} → {self.destination}")
            print(f"날짜: {self.departure_date} ~ {self.return_date}")
            print(f"인원: {self.adults}명")
            
            response = requests.get(
                self.search_url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"검색 성공! 응답 데이터 크기: {len(str(data))} bytes")
                return data
            else:
                print(f"API 오류: {response.status_code}")
                print(f"응답: {response.text}")
                return {}
                
        except requests.exceptions.Timeout:
            print("API 요청 시간 초과")
            return {}
        except requests.exceptions.RequestException as e:
            print(f"API 요청 실패: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 실패: {e}")
            return {}
    
    def parse_flights(self, data: Dict) -> List[Dict]:
        """검색 결과 파싱 (직항만 필터링)"""
        
        flights = []
        
        try:
            # RapidAPI 응답 구조에 따라 파싱
            itineraries = data.get('data', {}).get('itineraries', [])
            
            for itinerary in itineraries:
                # 가격 정보
                price_info = itinerary.get('price', {})
                total_price = price_info.get('raw', 0)
                
                # 2인 기준 총 가격
                total_for_two = total_price * self.adults
                
                # 가격 필터링
                if total_for_two > self.max_price:
                    continue
                
                # 구간 정보
                legs = itinerary.get('legs', [])
                if len(legs) < 2:  # 왕복이 아닌 경우 스킵
                    continue
                
                outbound = legs[0]
                inbound = legs[1]
                
                # 직항 여부 확인 (segments 개수가 1개면 직항)
                outbound_segments = outbound.get('segments', [])
                inbound_segments = inbound.get('segments', [])
                
                if self.direct_only:
                    if len(outbound_segments) > 1 or len(inbound_segments) > 1:
                        continue  # 경유 항공편 스킵
                
                # 항공사 정보
                carriers = outbound.get('carriers', {}).get('marketing', [])
                airline = carriers[0].get('name', 'Unknown') if carriers else 'Unknown'
                
                # 시간 정보
                outbound_departure = outbound.get('departure')
                outbound_arrival = outbound.get('arrival')
                inbound_departure = inbound.get('departure')
                inbound_arrival = inbound.get('arrival')
                
                flight_info = {
                    'airline': airline,
                    'price_per_person': total_price,
                    'price_total': total_for_two,
                    'currency': price_info.get('currency', 'KRW'),
                    'outbound': {
                        'departure': outbound_departure,
                        'arrival': outbound_arrival,
                        'duration': outbound.get('durationInMinutes', 0),
                        'stops': len(outbound_segments) - 1
                    },
                    'inbound': {
                        'departure': inbound_departure,
                        'arrival': inbound_arrival,
                        'duration': inbound.get('durationInMinutes', 0),
                        'stops': len(inbound_segments) - 1
                    },
                    'booking_link': itinerary.get('shareableUrl', '')
                }
                
                flights.append(flight_info)
            
            # 가격순 정렬
            flights.sort(key=lambda x: x['price_total'])
            
            print(f"직항 항공편 {len(flights)}개 발견 (150만원 이하)")
            
        except Exception as e:
            print(f"파싱 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return flights
    
    async def send_telegram_message(self, message: str):
        """텔레그램 메시지 전송"""
        try:
            await self.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print("텔레그램 메시지 전송 성공")
        except TelegramError as e:
            print(f"텔레그램 전송 실패: {e}")
    
    def format_time(self, datetime_str: str) -> str:
        """시간 포맷팅"""
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime('%H:%M')
        except:
            return datetime_str
    
    def format_duration(self, minutes: int) -> str:
        """비행 시간 포맷팅"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}시간 {mins}분"
    
    def format_message(self, flights: List[Dict]) -> str:
        """텔레그램 메시지 포맷팅"""
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if not flights:
            return (
                f"✈️ <b>항공편 모니터링</b>\n"
                f"📅 {self.departure_date} ~ {self.return_date}\n"
                f"👥 {self.adults}인 / 💺 직항\n"
                f"🔍 검색 시간: {current_time}\n\n"
                f"❌ 150만원 이하 직항 항공편이 없습니다."
            )
        
        message = (
            f"✈️ <b>항공편 발견! ({len(flights)}개)</b>\n"
            f"📅 {self.departure_date} ~ {self.return_date}\n"
            f"🛫 {self.origin} → {self.destination}\n"
            f"👥 {self.adults}인 / 💺 직항만\n"
            f"🔍 검색: {current_time}\n"
            f"{'='*30}\n\n"
        )
        
        for i, flight in enumerate(flights[:5], 1):  # 상위 5개만 표시
            price_total = flight['price_total']
            price_per = flight['price_per_person']
            
            message += (
                f"<b>{i}. {flight['airline']}</b>\n"
                f"💰 <b>총 {price_total:,}원</b> (1인 {price_per:,}원)\n"
            )
            
            # 가는편
            outbound = flight['outbound']
            message += (
                f"🛫 가는편: {self.format_time(outbound['departure'])} → "
                f"{self.format_time(outbound['arrival'])} "
                f"({self.format_duration(outbound['duration'])})\n"
            )
            
            # 오는편
            inbound = flight['inbound']
            message += (
                f"🛬 오는편: {self.format_time(inbound['departure'])} → "
                f"{self.format_time(inbound['arrival'])} "
                f"({self.format_duration(inbound['duration'])})\n"
            )
            
            # 예약 링크 (있는 경우)
            if flight.get('booking_link'):
                message += f"🔗 <a href=\"{flight['booking_link']}\">예약 링크</a>\n"
            
            message += "\n"
        
        # 특별 알림
        cheapest = flights[0]
        if cheapest['price_total'] <= 1200000:  # 120만원 이하
            message += (
                f"{'='*30}\n"
                f"🎯 <b>특가 알림!</b>\n"
                f"최저가가 120만원 이하입니다!\n"
                f"빠른 예약을 추천드립니다! 🏃‍♂️"
            )
        
        return message
    
    async def monitor_and_notify(self):
        """메인 모니터링 함수"""
        print(f"\n{'='*50}")
        print(f"항공편 모니터링 시작: {datetime.now()}")
        print(f"{'='*50}")
        
        # 항공편 검색
        data = self.search_flights()
        
        if not data:
            # API 오류 시 간단한 알림만
            await self.send_telegram_message(
                f"⚠️ 항공편 검색 실패\n"
                f"시간: {datetime.now().strftime('%H:%M')}\n"
                f"다음 검색: 30분 후"
            )
            return
        
        # 직항 항공편 파싱
        flights = self.parse_flights(data)
        
        # 메시지 생성 및 전송
        message = self.format_message(flights)
        await self.send_telegram_message(message)
        
        # 결과 요약 출력
        if flights:
            print(f"\n✅ 발견된 항공편:")
            for i, flight in enumerate(flights[:3], 1):
                print(f"  {i}. {flight['airline']}: {flight['price_total']:,}원")
        else:
            print("\n❌ 조건에 맞는 항공편 없음")
        
        print(f"\n모니터링 완료: {datetime.now()}")

async def main():
    """메인 실행 함수"""
    try:
        monitor = RapidAPIFlightMonitor()
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
                text=f"❌ 모니터링 오류 발생\n{str(e)}"
            )

if __name__ == "__main__":
    asyncio.run(main())
