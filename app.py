from flask import Flask, render_template, request, redirect, url_for, session
import numpy as np
import pandas as pd
import yfinance as yf
import re

from markowitz import markowitz_optimize

app = Flask(__name__)
app.secret_key = "sicuan"


# ======================
# FINANCIAL FUNCTIONS
# ======================

def future_value_lump_sum(pv, r, n):
    return pv * ((1 + r) ** n)


def future_value_annuity(pmt, r, n):
    if r == 0:
        return pmt * n
    return pmt * (((1 + r) ** n - 1) / r)


def parse_int(value):
    if not value:
        return 0
    value = re.sub(r"[^\d]", "", value)
    return int(value) if value else 0


# ======================
# SAHAM LIST
# ======================

BLUECHIP_STOCKS = [
    "BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ASII.JK",
    "UNVR.JK","ICBP.JK","INDF.JK","KLBF.JK","SIDO.JK",
    "CPIN.JK","JPFA.JK","MYOR.JK","SMGR.JK","INTP.JK",
    "AKRA.JK","AMRT.JK","ACES.JK","MAPI.JK","ERAA.JK"
]

GROWTH_STOCKS = [
    "ADRO.JK","PTBA.JK","ITMG.JK","ANTM.JK","INCO.JK",
    "MDKA.JK","PGAS.JK","BRPT.JK","ESSA.JK","TPIA.JK",
    "EXCL.JK","ISAT.JK","TBIG.JK","TOWR.JK","WIKA.JK",
    "PTPP.JK","ADHI.JK","MEDC.JK","HRUM.JK","GOTO.JK",
    "BRIS.JK","BUKA.JK","MAPA.JK","HMSP.JK","GGRM.JK"
]


# ======================
# MARKET ANALYSIS
# ======================

def get_trend(ticker):
    data = yf.download(ticker, period="6mo", interval="1d", progress=False)

    if data.empty or len(data) < 60:
        return "Sideways", 0

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA60"] = data["Close"].rolling(60).mean()

    ma20 = data["MA20"].iloc[-1]
    ma60 = data["MA60"].iloc[-1]
    price = int(data["Close"].iloc[-1])

    if ma20 > ma60 * 1.01:
        trend = "Naik (Uptrend)"
    elif ma20 < ma60 * 0.99:
        trend = "Turun (Downtrend)"
    else:
        trend = "Sideways"

    return trend, price


def score_stock(trend):
    if trend == "Naik (Uptrend)":
        return 3
    elif trend == "Sideways":
        return 2
    else:
        return 1


def select_top_stocks(stock_list, top_n=3):
    scored = []

    for kode in stock_list:
        trend, price = get_trend(kode)
        score = score_stock(trend)

        scored.append({
            "kode": kode.replace(".JK", ""),
            "trend": trend,
            "harga": price,
            "score": score
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def allocate_by_score(stocks, total_fund):
    total_score = sum(s["score"] for s in stocks) or 1
    sisa = total_fund

    for s in stocks:
        s["alokasi"] = int((s["score"] / total_score) * total_fund)
        sisa -= s["alokasi"]

    if stocks:
        stocks[0]["alokasi"] += sisa

    return stocks


# ======================
# ROUTES
# ======================

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/start", methods=["GET", "POST"])
def start():
    if request.method == "POST":
        session["user"] = {
            "nama": request.form.get("nama"),
            "nohp": request.form.get("nohp"),
            "email": request.form.get("email")
        }
        return redirect(url_for("profil_form"))

    return render_template("form.html")


@app.route("/profil", methods=["GET", "POST"])
def profil_form():
    if request.method == "POST":
        risk_score = sum(int(request.form.get(f"q{i}", 0)) for i in range(1, 9))
        session["risk_score"] = risk_score

        if risk_score <= 14:
            profil = "konservatif"
        elif risk_score <= 21:
            profil = "moderat"
        else:
            profil = "agresif"

        session["profil"] = profil
        return redirect(url_for("advisor"))

    return render_template("profil_form.html")


@app.route("/advisor", methods=["GET", "POST"])
def advisor():
    if request.method == "POST":

        tujuan = request.form.get("tujuan")
        dana_awal = parse_int(request.form.get("dana_awal"))
        target = parse_int(request.form.get("harga"))

        waktu_angka = int(request.form.get("waktu_angka") or 0)
        waktu_satuan = request.form.get("waktu_satuan")
        bulan = waktu_angka * 12 if waktu_satuan == "tahun" else waktu_angka

        profil = session.get("profil", "moderat")
        risk_score = session.get("risk_score", 18)

        kebutuhan_per_bulan = max(0, (target - dana_awal) // max(1, bulan))

        # ======================
        # PROFIL ANCHOR
        # ======================
        profil_alloc = {
            "konservatif": np.array([0.25, 0.30, 0.45]),
            "moderat":     np.array([0.40, 0.30, 0.30]),
            "agresif":     np.array([0.60, 0.25, 0.15])
        }[profil]

        # ======================
        # RISK INDEX
        # ======================
        SCORE_MIN, SCORE_MAX = 8, 24
        risk_index = (risk_score - SCORE_MIN) / (SCORE_MAX - SCORE_MIN)
        risk_index = min(max(risk_index, 0), 1)

        # ======================
        # ALPHA DINAMIS
        # ======================
        alpha = 0.7 - 0.2 * risk_index

        # ======================
        # MARKOWITZ
        # ======================
        returns = np.array([0.15, 0.10, 0.05])
        cov = np.array([
            [0.10, 0.02, 0.01],
            [0.02, 0.08, 0.01],
            [0.01, 0.01, 0.03]
        ])

        w_markowitz = np.array(markowitz_optimize(returns, cov))

        # ======================
        # HYBRID WEIGHT
        # ======================
        final_weight = alpha * profil_alloc + (1 - alpha) * w_markowitz
        final_weight = final_weight / final_weight.sum()

        dana_growth = int(dana_awal * final_weight[0])
        dana_bluechip = int(dana_awal * final_weight[1])
        dana_obligasi = int(dana_awal * final_weight[2])

        alokasi = [
            ("Saham Growth", round(final_weight[0] * 100, 1), dana_growth),
            ("Saham Blue Chip", round(final_weight[1] * 100, 1), dana_bluechip),
            ("Obligasi", round(final_weight[2] * 100, 1), dana_obligasi)
        ]

        growth_top = allocate_by_score(select_top_stocks(GROWTH_STOCKS), dana_growth)
        bluechip_top = allocate_by_score(select_top_stocks(BLUECHIP_STOCKS), dana_bluechip)

        r = 0.015
        fv_total = (
            future_value_lump_sum(dana_awal, r, bulan) +
            future_value_annuity(kebutuhan_per_bulan, r, bulan)
        )

        realistis = fv_total >= target

        result = {
            "tujuan": tujuan,
            "dana": dana_awal,
            "profil": profil.capitalize(),
            "kebutuhan_per_bulan": kebutuhan_per_bulan,
            "realistis": realistis,
            "alokasi": alokasi,
            "growth": growth_top,
            "bluechip": bluechip_top
        }

        return render_template("result.html", r=result)

    return render_template("advisor.html")


# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(debug=True, port=10000)
