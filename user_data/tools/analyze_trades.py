# Wertet den letzten Backtest aus: woran lagen Gewinner und Verlierer?
# Aufruf im freqtrade-Container: python3 user_data/tools/analyze_trades.py <split-datum YYYY-MM-DD>
# Alles vor dem Split-Datum ist "gelernt", danach "ungesehen" (zur Kontrolle, ob ein Muster haelt).
import sys

import pandas as pd
from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats

DIR = "user_data/backtest_results"
split = pd.Timestamp(sys.argv[1], tz="UTC")
stats = load_backtest_stats(DIR)
pd.set_option("display.width", 200)


def table(df, key):
    g = df.groupby(key)["profit_abs"]
    t = pd.DataFrame({"trades": g.size(), "summe$": g.sum().round(2),
                      "trefferquote%": (df.assign(w=df["profit_abs"] > 0).groupby(key)["w"].mean() * 100).round(0)})
    return t.sort_values("summe$")


alltrades = []
for name in stats["strategy"]:
    df = load_backtest_data(DIR, strategy=name)
    if df.empty:
        continue
    df["strategy"] = name
    alltrades.append(df)
df = pd.concat(alltrades)
df["hour"] = df["open_date"].dt.hour
df["weekday"] = df["open_date"].dt.day_name().str[:2]
df["minutes"] = (df["close_date"] - df["open_date"]).dt.total_seconds() // 60
df["dauer"] = pd.cut(df["minutes"], [0, 30, 60, 120, 240, 100000], labels=["<30m", "30-60m", "1-2h", "2-4h", ">4h"])
df["teil"] = (df["open_date"] >= split).map({False: "gelernt", True: "ungesehen"})
fees = (df["amount"] * df["open_rate"] * 0.002).sum() if "amount" in df else float("nan")
print(f"Trades: {len(df)}  Summe: {df['profit_abs'].sum():.2f} $  davon Gebuehren ca.: {fees:.2f} $")
for key in ["strategy", "exit_reason", "dauer", "hour", "weekday"]:
    print(f"\n== nach {key} (gelernt | ungesehen)")
    a = table(df[df["teil"] == "gelernt"], key)
    b = table(df[df["teil"] == "ungesehen"], key)
    print(a.join(b, lsuffix="_L", rsuffix="_U", how="outer").to_string())
print("\n== Coins (gelernt), 8 beste und 8 schlechteste")
c = table(df[df["teil"] == "gelernt"], "pair")
print(pd.concat([c.head(8), c.tail(8)]).to_string())
cu = table(df[df["teil"] == "ungesehen"], "pair")
best = c.tail(8).index
print(f"\nDieselben 8 besten Coins auf ungesehenen Tagen: {cu.reindex(best)['summe$'].sum():.2f} $")
