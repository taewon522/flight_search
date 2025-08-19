# python flight_search.py
# [쉬운] 이 파일은 아마데우스(Amadeus) API로 공항/항공권을 검색하는 예제입니다.
# [자세히] .env에 담긴 API 키를 읽어 클라이언트를 만들고,
#          1) 장소 검색 API(reference_data.locations)
#          2) 항공권 검색 API(shopping.flight_offers_search)
#          를 호출해 콘솔에 보기 좋은 형태로 출력합니다.

from amadeus import Client, ResponseError
# [쉬운] Amadeus SDK: API를 쉽게 호출하게 해주는 라이브러리.
# [자세히] Client는 인증/호스트(test/production) 설정을 감싸고,
#          ResponseError는 API 호출 실패 시 발생하는 예외 타입,
#          Location은 장소 검색 시 사용할 enum(공항/도시 등)입니다.

from dotenv import load_dotenv  # type: ignore
# [쉬운] .env 파일(환경변수) 읽어오는 함수.
# [자세히] 개발 중 민감한 값을 코드에 하드코딩하지 않고 .env에 두고 실행 시점에 로드합니다.

import os
# [쉬운] 환경변수(os.getenv) 읽을 때 사용.
# [자세히] 운영체제 레벨의 환경변수 접근, 경로 처리 등 유틸 제공.

import csv
# [쉬운] (선택) 결과를 CSV로 저장하고 싶을 때 쓰는 표준 모듈. (아래 코드에서는 사용 X)
# [자세히] csv.writer/csv.DictWriter 등으로 구조화된 텍스트 출력 가능.

import copy
# [쉬운] (선택) 딥카피/얕은카피 도구. (아래 코드에서는 사용 X)
# [자세히] 가변 객체를 복사할 때 원본 변경이 전파되지 않도록 deep copy가 필요할 수 있습니다.

from typing import Any, Dict, List
# [쉬운] 타입 힌트용 도구. dict 안 값이 뭐든 가능하도록 Any 사용.
# [자세히] mypy/Pylance 같은 타입 체커가 코드 품질을 도와줍니다. (런타임 동작엔 영향 없음)

load_dotenv()
# [쉬운] 현재 폴더의 .env 파일을 읽어 환경변수로 등록합니다.
# [자세히] 기본적으로 .env 경로를 자동 탐색합니다. 특정 경로가 필요하면 load_dotenv(".env.dev")처럼 지정.


from datetime import datetime, timezone

from pathlib import Path


# hostname: "test" 또는 "production"
amadeus = Client(
    client_id=os.getenv("AMADEUS_CLIENT_ID"),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
    hostname=os.getenv("AMADEUS_HOSTNAME", "test"),
)
# [쉬운] .env에서 키/시크릿/호스트를 읽어 Amadeus 클라이언트를 만듭니다.
# [자세히] test는 샌드박스, production은 실데이터/요금. production은 별도 권한과 쿼터가 있습니다.
#          os.getenv(key, default)로 값이 없으면 기본값("test")을 사용합니다.

def print_offer(idx: int, o: dict[str, Any]) -> None:
    # [쉬운] 항공권 하나를 사람이 읽기 쉽게 출력합니다.
    # [자세히] Amadeus Flight Offers 응답 스키마를 탐색해
    #          가격/통화/경로/출도착 시각/경유 수/항공편 번호/수하물 정보를 추출합니다.
    price = o["price"]["grandTotal"]
    currency = o["price"]["currency"]

    it = o["itineraries"][0]
    # [쉬운] 편도/왕복 중 첫 번째 여정(itinerary) 사용.
    # [자세히] offers[i].itineraries는 여러 여정이 올 수 있으며, 여기선 0번째만 표시.

    segs = it["segments"]
    # [쉬운] 실제 비행 구간들(직항이면 1개, 경유면 2개 이상)

    dep = segs[0]["departure"]
    arr = segs[-1]["arrival"]
    # [쉬운] 첫 구간의 출발, 마지막 구간의 도착이 전체 여정의 출발/도착입니다.
    # [자세히] 경유가 있어도 전체 여정의 시작/끝을 표현하기 위해 양 끝만 집계합니다.

    dep_time = dep["at"]
    arr_time = arr["at"]
    dep_airport = dep["iataCode"]
    arr_airport = arr["iataCode"]

    carrier = segs[0]["carrierCode"]
    flight_no = f'{carrier}{segs[0]["number"]}'
    # [쉬운] 첫 구간의 항공사 코드 + 편명으로 대표 표시.
    # [자세히] 구간마다 다른 항공사/코드셰어가 있을 수 있으나, 간단 출력을 위해 첫 구간 기준.

    duration = it.get("duration", "")
    # [쉬운] ISO 8601 기간(PTxHxM 형태) 문자열일 수 있습니다.
    # [자세히] 예: "PT2H30M" → 2시간 30분. 여기선 원문 그대로 노출.

    stops = len(segs) - 1
    # [쉬운] 경유 횟수 = 세그먼트 수 - 1

    # 수하물(가능 시)
    baggage = None
    for tp in o.get("travelerPricings", []):
        for fd in tp.get("fareDetailsBySegment", []):
            inc = fd.get("includedCheckedBags") or {}
            if "quantity" in inc:
                baggage = f'Checked x{inc["quantity"]}'
                break
            if "weight" in inc and "weightUnit" in inc:
                baggage = f'Checked {inc["weight"]}{inc["weightUnit"]}'
                break
        if baggage:
            break
    # [쉬운] 수하물 규정이 응답에 있으면 "개수" 또는 "무게" 기준으로 간단히 표시.
    # [자세히] 오퍼마다/탑승객 타입마다 규정이 다를 수 있어 travelerPricings → fareDetailsBySegment를 순회.
    #          정보가 없으면 표시 생략.
#
    print(
        f"[{idx}] {dep_airport}→{arr_airport}  {dep_time} → {arr_time}  "
        f"{'직항' if stops==0 else f'경유 {stops}회'}  {duration}  "
        f"{flight_no}  {price} {currency}"
        f"{'  | ' + baggage if baggage else ''}"
    )
    # [쉬운] 한 줄 요약 출력.
    # [자세히] 실제 서비스라면 콘솔 출력 대신 구조화(딕셔너리)하여 CSV/JSON 저장 또는 UI 렌더에 넘기는 걸 권장.


DATA_DIR = Path(__file__).with_name("data")
DATA_DIR.mkdir(exist_ok=True)

def csv_path(origin: str, dest: str, airline: str) -> Path:
    return DATA_DIR / f"prices_{origin.lower()}-{dest.lower()}_{airline.lower()}.csv"

def append_row(path: Path, row: Dict[str, Any]) -> None:
    header = [
        "collected_at_utc","travel_date","origin","dest","airline",
        "flight_no","dep_time","arr_time","stops","duration","price","currency"
    ]
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if is_new:
            w.writeheader()
        w.writerow(row)


def search_flights(origin, destination, date, adults, airline=None):
    # [쉬운] 데모로 항공권 검색을 실행합니다.
    # [자세히] 각 API 호출은 try/except로 감싸 실패 시 메시지를 표시합니다.

    #  항공권 검색 (ICN → NRT, 제주항공 7C, KRW)
    params = {
        "originLocationCode": origin,      # [쉬운] 출발: 인천
        "destinationLocationCode": destination, # [쉬운] 도착: 나리타 (하네다=HND)
        "departureDate": date,    # [쉬운] 출발 날짜 (YYYY-MM-DD)
        "adults": adults, # [쉬운] 성인 1명
        "currencyCode": "KRW",            # [쉬운] 금액 통화: 원화
        #"includedAirlineCodes": airline,     # [쉬운] 제주항공만 필터
        "max": 50,                        # [쉬운] 최대 50건 반환
    }
    # [자세히] 필요 시 returnDate, nonStop, travelClass, children, infants 등 다양한 파라미터가 있습니다.

    if airline:
        params["includedAirlineCodes"] = airline

    try:
        r = amadeus.shopping.flight_offers_search.get(**params)
        # [쉬운] 항공권 오퍼 검색 API 호출.
        # [자세히] GET /v2/shopping/flight-offers, 파라미터는 쿼리스트링으로 전달됩니다.

        offers = r.data
        results = []
        print(f"\n[Offers] 총 {len(offers)}건")

        for o in offers:
            results.append({
                "price": o["price"]["grandTotal"],
                "currency": o["price"]["currency"],
                "dep": o["itineraries"][0]["segments"][0]["departure"]["iataCode"],
                "arr": o["itineraries"][0]["segments"][-1]["arrival"]["iataCode"],
                "dep_time": o["itineraries"][0]["segments"][0]["departure"]["at"],
                "arr_time": o["itineraries"][0]["segments"][-1]["arrival"]["at"],
                "airline": o["itineraries"][0]["segments"][0]["carrierCode"],
                "flight_no": o["itineraries"][0]["segments"][0]["number"]
            })
        return results


#-------------------------------------------------------------------------------------------------------------
        #if offers:
        #    # 최저가 계산
        #    min_price = min(float(o["price"]["grandTotal"]) for o in offers)
        #    print(f"최저가: {min_price:.0f} KRW\n")
        #    # [자세히] 문자열로 오는 금액을 float로 변환해 비교. 통화 혼합 가능성은 currencyCode로 통일한 상태.
#
        #    # 상위 N건 요약 출력 (여기서는 전체 순회)
        #    for i, o in enumerate(offers[:], 1):
        #        print_offer(i, o)
        #else:
        #    print("검색 결과가 없습니다. 날짜/목적지/호스트(test/production)를 바꿔보세요.")
        #    # [자세히] test 호스트는 가끔 데이터가 제한적이라 날짜/항공사에 따라 결과가 없을 수 있습니다.
#--------------------------------------------------------------------------------------------------------------


    except ResponseError as e:
        return [{"Flight offers Search error": str(e)}]
        # print("Flight Offers Search 오류:", e)
        # [자세히] 잘못된 IATA 코드/유효하지 않은 날짜/쿼터 초과/인증 실패 등 API 에러 처리.




def search_lowest_fares(origin, dest, travel_date, adults, airline=None):

    #  항공권 검색 (ICN → NRT, 제주항공 7C, KRW)
    params2 = {
        "originLocationCode": origin,      # [쉬운] 출발: 인천
        "destinationLocationCode": dest, # [쉬운] 도착: 나리타 (하네다=HND)
        "departureDate": travel_date,    # [쉬운] 출발 날짜 (YYYY-MM-DD)
        "adults": 1, # [쉬운] 성인 1명
        "currencyCode": "KRW",            # [쉬운] 금액 통화: 원화
        #"includedAirlineCodes": airline,     # [쉬운] 제주항공만 필터
        "max": 50,                        # [쉬운] 최대 50건 반환
    }
    if airline:
        params2["includedAirlineCodes"] = airline

    try:
        r = amadeus.shopping.flight_offers_search.get(**params2)
        offers: List[Dict[str, Any]] = r.data or []
        if not offers:
            print("검색 결과가 없습니다.")
            return []

        best: Dict[str, Dict[str, Any]] = {}
        for o in offers:
            it = o["itineraries"][0]
            segs = it["segments"]
            airline = segs[0]["carrierCode"]
            if airline not in airline:
                continue
            price = float(o["price"]["grandTotal"])
            if (airline not in best) or (price < float(best[airline]["price"]["grandTotal"])):
                best[airline] = o

        now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
        results = []
        for al, o in sorted(best.items()):
            it = o["itineraries"][0]
            segs = it["segments"]
            dep = segs[0]["departure"]
            arr = segs[-1]["arrival"]
            row = {
                "collected_at_utc": now_utc,
                "travel_date": travel_date,
                "origin": origin,
                "dest": dest,
                "airline": al,
                "flight_no": f'{segs[0]["carrierCode"]}{segs[0]["number"]}',
                "dep_time": dep["at"],
                "arr_time": arr["at"],
                "stops": len(segs) - 1,
                "duration": it.get("duration",""),
                "price": float(o["price"]["grandTotal"]),
                "currency": o["price"]["currency"],
            }
            append_row(csv_path(origin, dest, al), row)
            print(f"{al}: {row['price']:.0f} {row['currency']} 저장됨")
            results.append(row)
        return results
    except ResponseError as e:
        print("Flight Offers Search 오류:", e)
        return []
