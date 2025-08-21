#!/usr/bin/env python3
"""
Amadeus API를 활용한 항공 가격 모니터링
2025년 10월 4일-8일 직항 항공편 모니터링
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
        
        # Amadeus API 엔드포인트 (테스트 환경)
        self.base_url = "https://test.api.amadeus.com"
        
        # OAuth2 토큰
        self.access_token = None
        self.token_expires_at = None
        
        # 한국 시간대 설정
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 모니터링 설정 (인천-호놀룰루, 10월 4일-8일)
        self.origin = "ICN"  # 인천공항
        self.destination = "HNL"  # 호놀룰루 (하와이)
        self.departure_date = "2025-10-04"  # 10월 4일로 변경
        self.return_date = "2025-10-08"
        self.adults = 2
        self.max_price = 3000000  # 150만원 (2인 총액)
        self.direct_only = True  # 직항만
        
    def get_access_token(self) -> str:
        """Amadeus OAuth2 토큰 획득"""
        
        # 토큰이 유효한 경우 재사용
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
            response = requests.post(token_url, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 1799)  # 기본 30분
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                print("인증 성공!")
                return self.access_token
            else:
                print(f"인증 실패: {response.status_code}")
                print(response.text)
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
            'nonStop': 'true' if self.direct_only else 'false',  # 직항만
            'currencyCode': 'KRW',  # 한국 원화
            'max': 50  # 최대 결과 수
        }
        
        try:
            # 한국 시간으로 표시
            kst_now = datetime.now(self.kst)
            print(f"\n[{kst_now.strftime('%H:%M:%S')} KST] 항공편 검색 중...")
            print(f"노선: {self.origin} → {self.destination} (인천-호놀룰루)")
            print(f"날짜: {self.departure_date} ~ {self.return_date}")
            print(f"인원: {self.adults}명, 직항만")
            
            response = requests.get(
                search_url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                offers = data.get('data', [])
                print(f"검색 성공! {len(offers)}개 항공편 발견")
                
                # 딕셔너리 정보도 포함
                result = {
                    'data': offers,
                    'dictionaries': data.get('dictionaries', {})
                }
                return result
            else:
                print(f"API 오류: {response.status_code}")
                print(f"응답: {response.text[:500]}")
                return {}
                
        except requests.exceptions.Timeout:
            print("API 요청 시간 초과")
            return {}
        except Exception as e:
            print(f"검색 오류: {e}")
            return {}
    
    def parse_flights(self, data: Dict) -> List[Dict]:
        """Amadeus API 응답 파싱"""
        
        flights = []
        offers = data.get('data', [])
        dictionaries = data.get('dictionaries', {})
        carriers = dictionaries.get('carriers', {})
        
        try:
            for offer in offers:
                # 가격 정보
                price_info = offer.get('price', {})
                total_price = float(price_info.get('total', '0'))
                
                # 150만원 이하만 필터링
                if total_price > self.max_price:
                    continue
                
                # 여정 정보
                itineraries = offer.get('itineraries', [])
                if len(itineraries) < 2:  # 왕복이 아닌 경우
                    continue
                
                outbound_itinerary = itineraries[0]
                return_itinerary = itineraries[1]
                
                # 직항 체크 (segments가 1개면 직항)
                outbound_segments = outbound_itinerary.get('segments', [])
                return_segments = return_itinerary.get('segments', [])
                
                if self.direct_only:
                    if len(outbound_segments) > 1 or len(return_segments) > 1:
                        continue
                
                # 항공사 정보
                outbound_carrier = outbound_segments[0].get('carrierCode', '') if outbound_segments else ''
                return_carrier = return_segments[0].get('carrierCode', '') if return_segments else ''
                
                # 항공사 이름 가져오기
                outbound_airline = self.get_airline_name(outbound_carrier)
                return_airline = self.get_airline_name(return_carrier)
                airline = outbound_airline if outbound_airline == return_airline else f"{outbound_airline}/{return_airline}"
                
                # 시간 정보
                outbound_segment = outbound_segments[0] if outbound_segments else {}
                return_segment = return_segments[0] if return_segments else {}
                
                flight_info = {
                    'carrier_code': outbound_carrier,  # 항공사 코드 저장
                    'airline': airline,
                    'price_per_person': total_price / self.adults,
                    'price_total': total_price,
                    'currency': price_info.get('currency', 'KRW'),
                    'outbound': {
                        'departure': outbound_segment.get('departure', {}).get('at', ''),
                        'arrival': outbound_segment.get('arrival', {}).get('at', ''),
                        'flight_no': f"{outbound_segment.get('carrierCode', '')}{outbound_segment.get('number', '')}",
                        'duration': outbound_itinerary.get('duration', ''),
                        'departure_terminal': outbound_segment.get('departure', {}).get('terminal', ''),
                        'arrival_terminal': outbound_segment.get('arrival', {}).get('terminal', '')
                    },
                    'inbound': {
                        'departure': return_segment.get('departure', {}).get('at', ''),
                        'arrival': return_segment.get('arrival', {}).get('at', ''),
                        'flight_no': f"{return_segment.get('carrierCode', '')}{return_segment.get('number', '')}",
                        'duration': return_itinerary.get('duration', ''),
                        'departure_terminal': return_segment.get('departure', {}).get('terminal', ''),
                        'arrival_terminal': return_segment.get('arrival', {}).get('terminal', '')
                    },
                    'booking_class': outbound_segment.get('cabin', 'ECONOMY'),
                    'available_seats': offer.get('numberOfBookableSeats', 'N/A')
                }
                
                flights.append(flight_info)
            
            # 가격순 정렬
            flights.sort(key=lambda x: x['price_total'])
            
            print(f"조건 충족 항공편: {len(flights)}개 (150만원 이하 직항)")
            
        except Exception as e:
            print(f"파싱 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return flights
    
    def format_duration(self, duration_str: str) -> str:
        """ISO 8601 duration을 읽기 쉬운 형식으로 변환"""
        # PT3H30M -> 3시간 30분
        try:
            duration_str = duration_str.replace('PT', '')
            hours = 0
            minutes = 0
            
            if 'H' in duration_str:
                hours_part = duration_str.split('H')[0]
                hours = int(hours_part)
                duration_str = duration_str.split('H')[1]
            
            if 'M' in duration_str:
                minutes_part = duration_str.replace('M', '')
                minutes = int(minutes_part)
            
            return f"{hours}시간 {minutes}분" if hours > 0 else f"{minutes}분"
        except:
            return duration_str
    
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
    
    def format_time(self, datetime_str: str) -> Tuple[str, str]:
        """시간 포맷팅 (시간, 날짜 반환)"""
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M')
            date_str = dt.strftime('%m/%d')
            return time_str, date_str
        except:
            return datetime_str[:5] if len(datetime_str) > 5 else datetime_str, ""
    
    def get_api_usage(self) -> str:
        """API 사용량 계산"""
        # 현재 날짜 기준 이번 달 사용 예상량 계산
        now = datetime.now()
        day_of_month = now.day
        runs_per_day = 48  # 30분마다 = 하루 48회
        estimated_usage = day_of_month * runs_per_day
        remaining = 2000 - estimated_usage
        
        return f"약 {remaining}회" if remaining > 0 else "한도 초과 예상"
    
    def get_airline_booking_url(self, carrier_code: str) -> str:
        """항공사 코드로 공식 예약 사이트 URL 생성"""
        
        # 날짜 포맷 변환
        dep_date = self.departure_date.replace('-', '')  # 20251004
        ret_date = self.return_date.replace('-', '')
        
        # 주요 항공사별 예약 링크
        airline_urls = {
            # 한국 항공사
            'KE': f'https://www.koreanair.com/booking/flights?departure={self.origin}&arrival={self.destination}&departure-date={self.departure_date}&return-date={self.return_date}',
            'OZ': f'https://flyasiana.com/booking/search?departure={self.origin}&arrival={self.destination}',
            'LJ': 'https://www.jinair.com/booking/index',
            '7C': 'https://www.jejuair.net/ko/main.do',
            'TW': 'https://www.twayair.com/main.do',
            'ZE': 'https://www.eastarjet.com/newstar/PGWBA00001',
            'BX': 'https://www.airbusan.com/content/individual/',
            'RS': 'https://www.airseoul.com/ko/main',
            
            # 일본 항공사
            'JL': f'https://www.jal.co.jp/jp/ja/',
            'NH': f'https://www.ana.co.jp/ja/jp/',
            
            # 미국 항공사 (하와이 노선)
            'HA': 'https://www.hawaiianairlines.co.kr/',
            'UA': 'https://www.united.com/ko/kr',
            'DL': 'https://www.delta.com/apac/ko',
            'AA': 'https://www.aa.com/homePage.do?locale=ko_KR',
            
            # 동남아 항공사
            'SQ': 'https://www.singaporeair.com/ko_KR',
            'TG': 'https://www.thaiairways.com/ko_KR/index.page',
            'VN': 'https://www.vietnamairlines.com/kr/ko/home',
            'PR': 'https://www.philippineairlines.com/ko-kr/kr/home',
            'MH': 'https://www.malaysiaairlines.com/kr/ko',
            
            # 중국 항공사
            'CA': 'https://www.airchina.kr/',
            'CZ': 'https://www.csair.com/kr/ko/',
            'MU': 'https://kr.ceair.com/',
            
            # 중동/유럽 항공사
            'EK': 'https://www.emirates.com/kr/korean/',
            'QR': 'https://www.qatarairways.com/ko-kr/homepage.html',
            'TK': 'https://www.turkishairlines.com/ko-kr/',
            'LH': 'https://www.lufthansa.com/kr/ko/homepage',
            'AF': 'https://www.airfrance.co.kr/',
        }
        
        # 항공사 코드에 해당하는 URL 반환
        return airline_urls.get(carrier_code, 'https://www.google.com/travel/flights')
    
    def get_airline_name(self, carrier_code: str) -> str:
        """항공사 코드를 한글 이름으로 변환"""
        airline_names = {
            'KE': '대한항공',
            'OZ': '아시아나',
            'LJ': '진에어',
            '7C': '제주항공',
            'TW': '티웨이',
            'ZE': '이스타항공',
            'BX': '에어부산',
            'RS': '에어서울',
            'HA': '하와이안항공',
            'JL': '일본항공',
            'NH': '전일본공수',
            'UA': '유나이티드',
            'DL': '델타',
            'AA': '아메리칸',
            'SQ': '싱가포르항공',
            'TG': '타이항공',
            'VN': '베트남항공',
            'PR': '필리핀항공',
            'MH': '말레이시아항공',
            'CA': '중국국제항공',
            'CZ': '중국남방항공',
            'MU': '중국동방항공',
            'EK': '에미레이트',
            'QR': '카타르항공',
            'TK': '터키항공',
            'LH': '루프트한자',
            'AF': '에어프랑스',
        }
        return airline_names.get(carrier_code, carrier_code)
    
    def get_booking_links(self, carrier_code: str = None) -> str:
        """항공권 검색 사이트 링크들"""
        links = ""
        
        # 특가 발견시 항공사 직접 링크 우선 제공
        if carrier_code:
            airline_url = self.get_airline_booking_url(carrier_code)
            airline_name = self.get_airline_name(carrier_code)
            links += (
                f"\n🎯 <b>항공사 직접 예약 (추천):</b>\n"
                f"✈️ <a href=\"{airline_url}\">{airline_name} 공식 홈페이지</a>\n"
            )
        
        # 기존 비교 사이트 링크들
        origin = self.origin
        dest = self.destination
        dep_date = self.departure_date
        ret_date = self.return_date
        
        # 구글 항공권 링크 생성
        google_url = f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{dest}+on+{dep_date}+return+{ret_date}"
        
        # 스카이스캐너 링크
        skyscanner_url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{dep_date.replace('-', '')}/{ret_date.replace('-', '')}/?adults={self.adults}"
        
        # 카약 링크
        kayak_url = f"https://www.kayak.co.kr/flights/{origin}-{dest}/{dep_date}/{ret_date}/{self.adults}adults"
        
        links += (
            f"\n💡 <b>가격 비교 사이트:</b>\n"
            f"🔗 <a href=\"{google_url}\">구글 항공권</a>\n"
            f"🔗 <a href=\"{skyscanner_url}\">스카이스캐너</a>\n"
            f"🔗 <a href=\"{kayak_url}\">카약</a>"
        )
        
        return links
    
    def format_message(self, flights: List[Dict]) -> str:
        """텔레그램 메시지 포맷팅"""

        kst_now = datetime.now(self.kst)
        current_time = kst_now.strftime('%Y-%m-%d %H:%M')
        api_remaining = self.get_api_usage()
        
        # 특가 발견시 첫 번째 항공사 코드 가져오기
        carrier_code = flights[0].get('carrier_code') if flights else None
        booking_links = self.get_booking_links(carrier_code)
        
        if not flights:
            return (
                f"✈️ <b>항공편 모니터링 (Amadeus)</b>\n"
                f"📅 {self.departure_date} ~ {self.return_date}\n"
                f"🛫 {self.origin} → {self.destination}\n"
                f"👥 {self.adults}인 / 💺 직항\n"
                f"🔍 검색 시간: {current_time}\n\n"
                f"❌ 150만원 이하 직항 항공편이 없습니다.\n"
                f"다음 검색: 30분 후\n"
                f"{booking_links}\n"
                f"\n{'='*30}\n"
                f"📊 API 잔여 횟수: {api_remaining}/2,000회"
            )
        
        # 특가 발견시 첫 번째 항공사 코드 가져오기
        carrier_code = flights[0].get('carrier_code') if flights else None
        booking_links = self.get_booking_links(carrier_code)
        
        message = (
            f"✈️ <b>항공편 발견! ({len(flights)}개)</b>\n"
            f"📅 {self.departure_date} ~ {self.return_date}\n"
            f"🛫 {self.origin} → {self.destination} (인천-호놀룰루)\n"
            f"👥 {self.adults}인 / 💺 직항만\n"
            f"🔍 검색: {current_time}\n"
            f"{'='*30}\n\n"
        )
        
        for i, flight in enumerate(flights[:5], 1):  # 상위 5개만 표시
            price_total = flight['price_total']
            price_per = flight['price_per_person']
            
            message += (
                f"<b>{i}. {flight['airline']}</b>\n"
                f"💰 <b>총 {price_total:,.0f}원</b> (1인 {price_per:,.0f}원)\n"
            )
            
            # 가는편
            outbound = flight['outbound']
            dep_time, dep_date = self.format_time(outbound['departure'])
            arr_time, arr_date = self.format_time(outbound['arrival'])
            
            message += f"🛫 가는편: {dep_time} → {arr_time} "
            if dep_date != arr_date:
                message += f"(+1일) "
            message += f"({self.format_duration(outbound['duration'])})\n"
            
            if outbound.get('flight_no'):
                message += f"   편명: {outbound['flight_no']}"
                if outbound.get('departure_terminal'):
                    message += f" (T{outbound['departure_terminal']})"
                message += "\n"
            
            # 오는편
            inbound = flight['inbound']
            dep_time, dep_date = self.format_time(inbound['departure'])
            arr_time, arr_date = self.format_time(inbound['arrival'])
            
            message += f"🛬 오는편: {dep_time} → {arr_time} "
            if dep_date != arr_date:
                message += f"(+1일) "
            message += f"({self.format_duration(inbound['duration'])})\n"
            
            if inbound.get('flight_no'):
                message += f"   편명: {inbound['flight_no']}"
                if inbound.get('departure_terminal'):
                    message += f" (T{inbound['departure_terminal']})"
                message += "\n"
            
            # 좌석 정보
            if flight.get('available_seats') != 'N/A':
                message += f"💺 예약 가능: {flight['available_seats']}석\n"
            
            # 클래스 정보
            if flight.get('booking_class'):
                class_map = {'ECONOMY': '이코노미', 'PREMIUM_ECONOMY': '프리미엄 이코노미', 
                           'BUSINESS': '비즈니스', 'FIRST': '퍼스트'}
                class_kr = class_map.get(flight['booking_class'], flight['booking_class'])
                message += f"🎫 클래스: {class_kr}\n"
            
            message += "\n"
        
        # 특별 알림
        if flights:
            cheapest = flights[0]
            airline_name = cheapest.get('airline', '항공사')
            
            if cheapest['price_total'] <= 1200000:  # 120만원 이하
                message += (
                    f"{'='*30}\n"
                    f"🎯 <b>특가 알림!</b>\n"
                    f"{airline_name} {cheapest['price_total']:,.0f}원 (120만원 이하)\n"
                    f"빠른 예약을 추천드립니다! 🏃‍♂️"
                )
            elif cheapest['price_total'] <= 1350000:  # 135만원 이하
                message += (
                    f"{'='*30}\n"
                    f"💡 <b>좋은 가격 발견!</b>\n"
                    f"{airline_name} {cheapest['price_total']:,.0f}원"
                )
        
        # 예약 사이트 링크 추가
        message += f"\n{booking_links}"
        
        # API 잔여 한도 정보
        message += (
            f"\n{'='*30}\n"
            f"📊 API 잔여 횟수: {api_remaining}/2,000회"
        )
        
        return message
    
    async def monitor_and_notify(self):
        """메인 모니터링 함수 - 클래스 메서드로 정의"""
        kst_now = datetime.now(self.kst)
        
        print(f"\n{'='*50}")
        print(f"Amadeus API 항공편 모니터링 시작")
        print(f"시간: {kst_now.strftime('%Y-%m-%d %H:%M:%S KST')}")
        print(f"노선: 인천(ICN) → 호놀룰루(HNL)")
        print(f"{'='*50}")
        
        # 항공편 검색
        data = self.search_flights()
        
        if not data:
            # API 오류 시 간단한 알림
            await self.send_telegram_message(
                f"⚠️ 항공편 검색 실패\n"
                f"시간: {kst_now.strftime('%H:%M KST')}\n"
                f"API 상태를 확인하세요.\n"
                f"다음 검색: 30분 후"
            )
            return
        
        # 항공편 파싱
        flights = self.parse_flights(data)
        
        # 메시지 생성 및 전송
        message = self.format_message(flights)
        await self.send_telegram_message(message)
        
        # 결과 요약 출력
        if flights:
            print(f"\n✅ 발견된 항공편 TOP 3:")
            for i, flight in enumerate(flights[:3], 1):
                print(f"  {i}. {flight['airline']}: {flight['price_total']:,.0f}원")
        else:
            print("\n❌ 조건에 맞는 항공편 없음")
        
        kst_end = datetime.now(self.kst)
        print(f"\n모니터링 완료: {kst_end.strftime('%Y-%m-%d %H:%M:%S KST')}")
        print(f"다음 실행: 30분 후 (GitHub Actions 스케줄)")

# 메인 실행 함수 (클래스 밖에 정의)
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
