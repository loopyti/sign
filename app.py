import os, json, requests
import swisseph as swe
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
from datetime import datetime

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

def gemini(prompt: str) -> str:
    r = requests.post(GEMINI_URL,
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def gemini_chat(messages: list) -> str:
    r = requests.post(GEMINI_URL,
        json={"contents": messages},
        timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO, "North Node": swe.MEAN_NODE, "Chiron": swe.CHIRON,
}
SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
ASPECTS = {
    "Conjunction":(0,10), "Opposition":(180,10), "Trine":(120,10),
    "Square":(90,10), "Sextile":(60,6),
}

def deg_to_sign(lon):
    return SIGNS[int(lon//30)], round(lon % 30, 2)

def calc_aspect(l1, l2):
    diff = abs(l1 - l2)
    if diff > 180: diff = 360 - diff
    for name, (angle, orb) in ASPECTS.items():
        o = abs(diff - angle)
        if o <= orb:
            return name, round(o, 2)
    return None, None

class BirthInput(BaseModel):
    year: int; month: int; day: int
    hour: int; minute: int
    city: str; country: str

class ChatRequest(BaseModel):
    chart_json: str
    messages: list[dict]
    new_message: str

async def geocode(city, country):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get("https://nominatim.openstreetmap.org/search",
            params={"q": f"{city}, {country}", "format": "json", "limit": 1},
            headers={"User-Agent": "AstrologyApp/1.0"})
        data = r.json()
    if not data:
        raise ValueError(f"'{city}'를 찾을 수 없습니다. 다른 도시명으로 시도해보세요.")
    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    tz = TimezoneFinder().timezone_at(lat=lat, lng=lon)
    if not tz:
        raise ValueError("해당 위치의 시간대를 찾을 수 없습니다.")
    return lat, lon, tz

def calculate_chart(utc_dt, lat, lon, tz_name, utc_offset):
    ephe_path = os.environ.get("EPHE_PATH", "/content/ephe")
    swe.set_ephe_path(ephe_path)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                    utc_dt.hour + utc_dt.minute/60.0)
    _, ascmc = swe.houses(jd, lat, lon, b"W")
    asc_lon, mc_lon = ascmc[0], ascmc[1]
    asc_sign, _ = deg_to_sign(asc_lon)
    mc_sign, _  = deg_to_sign(mc_lon)
    asc_idx = SIGNS.index(asc_sign)

    houses = [{"house": i+1, "sign": SIGNS[(asc_idx+i)%12]} for i in range(12)]

    planet_lons = {}
    planets = []
    for name, pid in PLANETS.items():
        res, _ = swe.calc_ut(jd, pid)
        lon_p, speed = res[0], res[3]
        sign, deg = deg_to_sign(lon_p)
        house = (SIGNS.index(sign) - asc_idx) % 12 + 1
        planet_lons[name] = lon_p
        planets.append({"name": name, "sign": sign, "degree": deg,
                        "house": house, "retrograde": speed < 0})

    # Lilith
    lil, _ = swe.calc_ut(jd, swe.MEAN_APOG)
    ls, ld = deg_to_sign(lil[0])
    planet_lons["Lilith"] = lil[0]
    planets.append({"name":"Lilith","sign":ls,"degree":ld,
                    "house":(SIGNS.index(ls)-asc_idx)%12+1,"retrograde":False})

    # Fortune
    f_lon = (asc_lon + planet_lons["Moon"] - planet_lons["Sun"]) % 360
    fs, fd = deg_to_sign(f_lon)
    planet_lons["Fortune"] = f_lon
    planets.append({"name":"Fortune","sign":fs,"degree":fd,
                    "house":(SIGNS.index(fs)-asc_idx)%12+1,"retrograde":False})

    # Planet aspects
    pnames = list(planet_lons.keys())
    aspects = []
    for i in range(len(pnames)):
        for j in range(i+1, len(pnames)):
            a, orb = calc_aspect(planet_lons[pnames[i]], planet_lons[pnames[j]])
            if a:
                aspects.append({"planet1":pnames[i],"planet2":pnames[j],
                                "type":a,"orb":orb})

    # Other aspects (ASC, DSC, MC, IC)
    dsc_lon = (asc_lon + 180) % 360
    ic_lon  = (mc_lon  + 180) % 360
    extra = {"ASC": asc_lon, "DSC": dsc_lon, "MC": mc_lon, "IC": ic_lon}

    other_aspects = []
    for pt_name, pt_lon in extra.items():
        for pl_name, pl_lon in planet_lons.items():
            a, orb = calc_aspect(pt_lon, pl_lon)
            if a:
                other_aspects.append({"planet1":pt_name,"planet2":pl_name,
                                      "type":a,"orb":orb})

    return {"asc": asc_sign, "mc": mc_sign, "planets": planets,
            "houses": houses, "aspects": aspects, "other_aspects": other_aspects,
            "timezone": tz_name, "utc_offset": utc_offset}

@app.get("/", response_class=HTMLResponse)
async def serve_html():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/api/chart")
async def get_chart(birth: BirthInput):
    try:
        lat, lon, tz = await geocode(birth.city, birth.country)
    except ValueError as e:
        raise HTTPException(422, str(e))

    local_dt = datetime(birth.year, birth.month, birth.day,
                        birth.hour, birth.minute, tzinfo=ZoneInfo(tz))
    utc_offset = local_dt.utcoffset().total_seconds() / 3600
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

    try:
        chart = calculate_chart(utc_dt, lat, lon, tz, utc_offset)
    except Exception as e:
        raise HTTPException(500, f"차트 계산 오류: {str(e)}")

    chart_json = json.dumps(chart, ensure_ascii=False)
    prompt = f"""당신은 서양 점성술 전문가입니다. Whole Sign 하우스 기준으로 분석하고 한국어로 답하세요.

출생 차트:
```json
{chart_json}
```

다음 순서로 따뜻하고 깊이 있게 분석해주세요:
1. 전체 차트 특성 (ASC, Sun, Moon)
2. 주요 행성 배치 의미
3. 중요 어스펙트 해석
4. 삶의 주요 테마 (직업, 관계, 성장)
5. 2026년 월별 금전,관계,연애,가족,직업
6. 조언"""

    try:
        analysis = gemini(prompt)
    except Exception as e:
        raise HTTPException(503, f"AI 분석 오류: {str(e)}")

    return {"chart": chart, "chart_json": chart_json, "analysis": analysis}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    system = f"당신은 서양 점성술 전문가입니다. 한국어로 답하세요.\n사용자 출생 차트: {req.chart_json}"

    messages = req.messages.copy()
    if messages and messages[0]["role"] == "user":
        messages[0] = {"role": "user", "parts": [system + "\n\n" + messages[0]["parts"][0]]}
    else:
        messages.insert(0, {"role": "user", "parts": [system]})
        messages.insert(1, {"role": "model", "parts": ["네, 차트를 확인했습니다. 무엇이 궁금하신가요?" ]})

    messages.append({"role": "user", "parts": [req.new_message]})

    try:
        reply = gemini_chat(messages)
    except Exception as e:
        raise HTTPException(503, f"AI 응답 오류: {str(e)}")

    updated = req.messages + [
        {"role": "user", "parts": [req.new_message]},
        {"role": "model", "parts": [reply]}
    ]
    return {"reply": reply, "messages": updated}
