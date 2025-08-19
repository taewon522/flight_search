from flask import Flask, render_template, request, jsonify
from flight_search import search_flights, search_lowest_fares
import pandas as pd

app = Flask(__name__)

# CSV 로드
df = pd.read_csv("국토교통부_세계공항_정보_20241231.csv", encoding="cp949")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# 도시명으로 공항 검색 (Ajax 호출)
@app.route("/api/airports")
def get_airports():
    city = request.args.get("city", "").lower().strip()
    results = []

    matches = df[
        df["영문도시명"].str.lower().str.contains(city, na=False) |
        df["한글공항"].str.contains(city, na=False) |
        df["한글국가명"].str.contains(city, na=False)
    ]

    for _, row in matches.iterrows():
        if pd.notna(row["공항코드1(IATA)"]):
            results.append({
                "city": row["영문도시명"],
                "code": row["공항코드1(IATA)"],
                "name": row["영문공항명"],
                "name_kr": row["한글공항"],
                "country": row["한글국가명"]
            })

    return jsonify(results)


# 항공권 검색
@app.route("/search", methods=["POST"])
def search():
    origin = request.form.get("origin")
    destination = request.form.get("destination")
    date = request.form.get("date")
    adults = request.form.get("adults")
    airline = request.form.get("airline")

    results = search_flights(origin, destination, date, adults, airline)
    return render_template("results.html", result=results)


@app.route("/lowest", methods=["POST"])
def lowest():
    origin = request.form.get("origin")
    dest = request.form.get("destination")
    travel_date = request.form.get("date")
    adults = request.form.get("adults")
    airline = request.form.get("airline")

    results = search_lowest_fares(origin, dest, travel_date, adults, airline)
    return render_template("results.html", result=results, mode="최저가 검색")

if __name__ == "__main__":
    app.run(debug=True)