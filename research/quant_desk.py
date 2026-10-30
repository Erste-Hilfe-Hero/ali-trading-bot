"""Overnight quant desk: rule-based long-only spot strategies on BTC/ETH/SOL.

Data: Binance spot 1h klines, Binance USD-M funding history, DefiLlama stablecoin supply.
Costs: 0.1% fee + 0.05% slippage per side (0.3% round trip).
Signals use only closed bars; entries fill at the next bar's open.
Parameters are picked on the in-sample period only; out-of-sample is reported untouched.
"""
import itertools
import json
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

COINS = ["BTC", "ETH", "SOL"]
START = "2020-09-01"
SPLIT = "2024-01-01"
FEE = 0.001
SLIP = 0.0005
COST = FEE + SLIP
DATA = os.environ.get("QD_DATA", "user_data/research")


def get(url):
    for i in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            print("retry", url[:90], e, flush=True)
            time.sleep(2 ** i)
    raise RuntimeError(url)


def klines(sym):
    path = f"{DATA}/{sym}_1h.csv"
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 6 * 3600:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    t = int(pd.Timestamp(START, tz="UTC").timestamp() * 1000)
    rows = []
    while True:
        k = get(f"https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=1h&startTime={t}&limit=1000")
        if not k:
            break
        rows += k
        t = k[-1][0] + 3600_000
        if len(k) < 1000:
            break
    df = pd.DataFrame([r[:6] for r in rows], columns=["t", "o", "h", "l", "c", "v"]).astype(float)
    df.index = pd.to_datetime(df.pop("t"), unit="ms")
    df = df[df.index < pd.Timestamp.utcnow().tz_localize(None).floor("h")]
    df.to_csv(path)
    return df


def funding(sym):
    path = f"{DATA}/{sym}_funding.csv"
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 6 * 3600:
        return pd.read_csv(path, index_col=0, parse_dates=True)["rate"]
    t = int(pd.Timestamp(START, tz="UTC").timestamp() * 1000)
    rows = []
    while True:
        k = get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}USDT&startTime={t}&limit=1000")
        if not k:
            break
        rows += k
        t = k[-1]["fundingTime"] + 1
        if len(k) < 1000:
            break
    s = pd.Series([float(r["fundingRate"]) for r in rows],
                  index=pd.to_datetime([r["fundingTime"] for r in rows], unit="ms"), name="rate")
    s.to_frame().to_csv(path)
    return s


def stables():
    try:
        d = get("https://stablecoins.llama.fi/stablecoincharts/all")
        s = pd.Series([float(x["totalCirculatingUSD"].get("peggedUSD", 0)) for x in d],
                      index=pd.to_datetime([int(x["date"]) for x in d], unit="s"))
        return s[s.index >= "2020-01-01"]
    except Exception as e:
        print("DefiLlama nicht erreichbar:", e)
        return None


def atr(df, n):
    pc = df.c.shift()
    tr = pd.concat([df.h - df.l, (df.h - pc).abs(), (df.l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def daily(df):
    return df.resample("1D").agg({"o": "first", "h": "max", "l": "min", "c": "last", "v": "sum"}).dropna()


def simulate(df, entry, exit_sig=None, stop=None, stop_atr=None, trail_atr=None, target=None, hold=None, atr_n=14):
    """Long-only, one position. Returns (trades list, per-bar strategy return Series)."""
    o, h, l, c = (df[x].to_numpy() for x in "ohlc")
    en = entry.reindex(df.index).fillna(False).to_numpy(bool)
    ex = exit_sig.reindex(df.index).fillna(False).to_numpy(bool) if exit_sig is not None else np.zeros(len(df), bool)
    a = atr(df, atr_n).to_numpy()
    n = len(df)
    ret = np.zeros(n)
    trades = []
    i = 0
    while i < n - 1:
        if not en[i] or np.isnan(a[i]):
            i += 1
            continue
        j = i + 1
        fill = o[j] * (1 + SLIP)
        sp = -np.inf
        if stop:
            sp = fill * (1 - stop)
        if stop_atr:
            sp = max(sp, fill - stop_atr * a[i])
        tp = fill * (1 + target) if target else np.inf
        hi, ref = fill, fill
        ret[j] -= FEE
        k = j
        out = None
        while k < n:
            px = None
            if k > j and o[k] <= sp:
                px = o[k]
            elif l[k] <= sp:
                px = sp
            elif h[k] >= tp:
                px = o[k] if k > j and o[k] >= tp else tp
            elif hold and k - j + 1 >= hold:
                px = c[k]
            if px is not None:
                out = (k, px)
                break
            ret[k] += c[k] / ref - 1
            ref = c[k]
            if trail_atr:
                hi = max(hi, c[k])
                sp = max(sp, hi - trail_atr * a[k])
            if ex[k] and k + 1 < n:
                out = (k + 1, o[k + 1])
                break
            k += 1
        if out is None:
            out = (n - 1, c[n - 1])
        k, px = out
        ret[k] += px * (1 - SLIP) / ref - 1 - FEE
        trades.append((df.index[j], df.index[k], px * (1 - SLIP) * (1 - FEE) / (fill * (1 + FEE)) - 1))
        i = k
    return trades, pd.Series(ret, index=df.index)


def stats(trades, rets, lo=None, hi=None):
    t = pd.DataFrame(trades, columns=["entry", "exit", "r", "coin", "w"]) if trades else pd.DataFrame(columns=["entry", "exit", "r", "coin", "w"])
    r = rets
    if lo:
        t = t[t.entry >= lo]
        r = r[r.index >= lo]
    if hi:
        t = t[t.entry < hi]
        r = r[r.index < hi]
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min() if len(eq) else 0
    g = t.r[t.r > 0].sum()
    ls = -t.r[t.r < 0].sum()
    yrs = max((r.index[-1] - r.index[0]).days / 365.25, 1e-9) if len(r) else 1
    tot = eq.iloc[-1] - 1 if len(eq) else 0
    m = (1 + r).resample("ME").prod() - 1 if len(r) else pd.Series(dtype=float)
    return dict(n=len(t), win=(t.r > 0).mean() if len(t) else 0, pf=g / ls if ls > 0 else (np.inf if g > 0 else 0),
                ret=tot, cagr=(1 + tot) ** (1 / yrs) - 1 if tot > -1 else -1, dd=dd,
                worst=m.min() if len(m) else 0, worst_m=str(m.idxmin())[:7] if len(m) else "", avg=t.r.mean() if len(t) else 0)


def score(full, oos, reg):
    s1 = 1 if full["cagr"] <= 0 else 2 if full["cagr"] < .05 else 3 if full["cagr"] < .15 else 4 if full["cagr"] < .30 else 5
    d = -full["dd"]
    s2 = 1 if d > .4 else 2 if d > .3 else 3 if d > .2 else 4 if d > .1 else 5
    s3 = 1 if full["n"] < 30 else 2 if full["n"] < 100 else 3 if full["n"] < 200 else 4 if full["n"] < 500 else 5
    p = oos["pf"]
    s4 = 1 if p < 1 or oos["n"] < 10 else 2 if p < 1.1 else 3 if p < 1.3 else 4 if p < 1.6 else 5
    pos = sum(1 for v in reg.values() if v["sum"] > 0)
    s5 = [1, 2, 3, 4][pos] if pos < 3 else (5 if all(v["pf"] > 1.2 for v in reg.values()) else 4)
    return s1 + s2 + s3 + s4 + s5, (s1, s2, s3, s4, s5)


def main():
    os.makedirs(DATA, exist_ok=True)
    H = {k: klines(k) for k in COINS}
    for k in COINS:
        print(k, "1h", H[k].index[0], "->", H[k].index[-1], len(H[k]), "Kerzen", flush=True)
    F = {}
    for k in COINS:
        try:
            F[k] = funding(k)
            print(k, "Funding", F[k].index[0], "->", F[k].index[-1], len(F[k]), flush=True)
        except Exception as e:
            print(k, "Funding fehlt:", e)
    ST = stables()
    if ST is not None:
        print("Stablecoins", ST.index[0], "->", ST.index[-1], len(ST))
    D = {k: daily(H[k]) for k in COINS}

    # BTC regime per day (known at day close, applied from next day): bull/bear/chop
    b = D["BTC"].c
    sma = b.rolling(200).mean()
    reg = np.where((b > sma) & (sma > sma.shift(30)), "bull", np.where((b < sma) & (sma < sma.shift(30)), "bear", "chop"))
    REG = pd.Series(reg, index=b.index).shift(1)
    print("Regime-Tage:", REG.value_counts().to_dict())

    def H_ret(k, n):
        return H[k].c.pct_change(n)

    fams = {}

    # 1 Funding extremes: crowded shorts pay longs -> buy spot, hold
    def funding_fam(thr, hold, stop):
        out = {}
        for k in COINS:
            if k not in F:
                return None
            f = F[k].reindex(H[k].index, method="ffill")
            out[k] = (H[k], f < thr, dict(hold=hold, stop=stop))
        return out
    fams["Funding-Extrem"] = (funding_fam, dict(thr=[-0.0001, -0.0002, -0.0003, -0.0005], hold=[24, 72, 168], stop=[0.05, 0.10]))

    # 2a Squeeze breakout (daily): tight Bollinger width then close above 20d high
    def squeeze_fam(q, lb, trail):
        out = {}
        for k in COINS:
            d = D[k]
            m = d.c.rolling(20).mean()
            w = 4 * d.c.rolling(20).std() / m
            tight = w.rolling(10).min() <= w.rolling(180).quantile(q)
            brk = d.c > d.h.shift(1).rolling(lb).max()
            out[k] = (d, tight & brk, dict(stop_atr=2, trail_atr=trail))
        return out
    fams["Range-Ausbruch (Squeeze)"] = (squeeze_fam, dict(q=[0.1, 0.2, 0.3], lb=[10, 20], trail=[2, 3, 4]))

    # 2b Donchian trend breakout (daily)
    def donchian_fam(n_in, n_out):
        out = {}
        for k in COINS:
            d = D[k]
            out[k] = (d, d.c > d.h.shift(1).rolling(n_in).max(), dict(exit_sig=d.c < d.l.shift(1).rolling(n_out).min(), stop_atr=2.5))
        return out
    fams["Donchian-Ausbruch"] = (donchian_fam, dict(n_in=[20, 30, 55], n_out=[10, 20]))

    # 3 BTC leads alts (1h): BTC jumps, alt has not followed yet
    def lead_fam(x, lag, hold):
        out = {}
        br = H_ret("BTC", 1)
        for k in ["ETH", "SOL"]:
            ar = H_ret(k, 1).reindex(br.index)
            out[k] = (H[k], (br > x) & (ar < lag * br), dict(hold=hold, stop=0.03))
        return out
    fams["BTC fuehrt Altcoins"] = (lead_fam, dict(x=[0.01, 0.015, 0.02], lag=[0.3, 0.6], hold=[2, 4, 8, 24]))

    # 4 Snap-back after sharp drop (1h)
    def snap_fam(n, drop, hold, stop):
        out = {}
        for k in COINS:
            out[k] = (H[k], H_ret(k, n) < -drop, dict(hold=hold, stop=stop))
        return out
    fams["Snap-back nach Absturz"] = (snap_fam, dict(n=[4, 12, 24], drop=[0.05, 0.08, 0.12], hold=[12, 24, 72], stop=[0.05, 0.10]))

    # 5 Day of week (daily): enter at open of weekday dow, hold `days`
    def dow_fam(dow, days):
        out = {}
        for k in COINS:
            d = D[k]
            sig = pd.Series((d.index + pd.Timedelta(days=1)).dayofweek == dow, index=d.index)
            out[k] = (d, sig, dict(hold=days))
        return out
    fams["Wochentag"] = (dow_fam, dict(dow=list(range(7)), days=[1, 2, 3]))

    # 6 Time-series trend (daily): above SMA -> hold, below -> out
    def sma_fam(n):
        out = {}
        for k in COINS:
            d = D[k]
            m = d.c.rolling(n).mean()
            out[k] = (d, d.c > m, dict(exit_sig=d.c < m))
        return out
    fams["Trend ueber SMA"] = (sma_fam, dict(n=[50, 100, 150, 200]))

    # 6b Weekly momentum (daily bars, decided on Mondays)
    def mom_fam(lb, filt):
        out = {}
        for k in COINS:
            d = D[k]
            mon = pd.Series((d.index + pd.Timedelta(days=1)).dayofweek == 0, index=d.index)
            up = d.c.pct_change(lb) > 0
            if filt:
                up &= d.c > d.c.rolling(200).mean()
            out[k] = (d, mon & up, dict(exit_sig=mon & ~up))
        return out
    fams["Wochen-Momentum"] = (mom_fam, dict(lb=[28, 56, 84], filt=[False, True]))

    # 7 Stablecoin supply growth (daily, lagged one extra day)
    if ST is not None:
        def stable_fam(lb, thr):
            out = {}
            g = ST.pct_change(lb).shift(1)
            for k in COINS:
                d = D[k]
                gg = g.reindex(d.index, method="ffill")
                out[k] = (d, gg > thr, dict(exit_sig=gg < 0))
            return out
        fams["Stablecoin-Zufluss"] = (stable_fam, dict(lb=[7, 14, 30], thr=[0.005, 0.01, 0.02, 0.03]))

    def run(build, params):
        legs = build(**params)
        if legs is None:
            return None
        w = 1 / len(legs)
        trades, rets = [], []
        for k, (df, en, kw) in legs.items():
            tr, r = simulate(df, en, **kw)
            trades += [(a, b, x, k, w) for a, b, x in tr]
            rets.append(r.resample("1D").apply(lambda s: (1 + s).prod() - 1) * w if (df.index[1] - df.index[0]) < pd.Timedelta("1D") else r * w)
        R = pd.concat(rets, axis=1).fillna(0).sum(axis=1)
        R = R[R.index >= START]
        return trades, R

    bh = pd.concat([D[k].c.pct_change() / 3 for k in COINS], axis=1).fillna(0).sum(axis=1)
    bh = bh[bh.index >= START]
    bs = stats([], bh)
    print(f"\nBuy&Hold 1/3 je Coin: Rendite {bs['ret']:+.0%}, CAGR {bs['cagr']:+.0%}, max DD {bs['dd']:.0%}, schlechtester Monat {bs['worst']:+.0%} ({bs['worst_m']})")
    bi, bo = stats([], bh, hi=SPLIT), stats([], bh, lo=SPLIT)
    print(f"  In-Sample {bi['ret']:+.0%} (DD {bi['dd']:.0%}), Out-of-Sample {bo['ret']:+.0%} (DD {bo['dd']:.0%})")

    results = []
    for name, (build, grid) in fams.items():
        keys = list(grid)
        rows = []
        for vals in itertools.product(*grid.values()):
            p = dict(zip(keys, vals))
            out = run(build, p)
            if out is None:
                break
            tr, R = out
            rows.append((p, stats(tr, R, hi=SPLIT), stats(tr, R, lo=SPLIT), stats(tr, R), tr, R))
        if not rows:
            print(f"\n## {name}: keine Daten")
            continue
        ok = [x for x in rows if x[1]["n"] >= 20] or rows
        best = max(ok, key=lambda x: (min(x[1]["pf"], 10), x[1]["cagr"]))
        p, ins, oos, full, tr, R = best
        oos_pos = sum(1 for x in rows if x[2]["pf"] > 1 and x[2]["n"] >= 10)
        t = pd.DataFrame(tr, columns=["entry", "exit", "r", "coin", "w"])
        t["reg"] = REG.reindex(t.entry.dt.floor("D")).to_numpy()
        reg = {}
        for rg in ["bull", "bear", "chop"]:
            x = t[t.reg == rg]
            g, l = x.r[x.r > 0].sum(), -x.r[x.r < 0].sum()
            reg[rg] = dict(n=len(x), sum=(x.r * x.w).sum(), pf=g / l if l > 0 else (9.99 if g > 0 else 0))
        sc, parts = score(full, oos, reg)
        keep = sc >= 18 and full["pf"] > 1.3 and full["dd"] > -0.2 and full["n"] >= 100
        results.append((name, p, sc, keep))
        print(f"\n## {name}  | Gitter {len(rows)} Varianten, davon {oos_pos} mit OOS-PF>1")
        print(f"   gewaehlt (nur In-Sample): {p}")
        for lab, s in [("In-Sample 2020-09..2023", ins), ("Out-of-Sample 2024..heute", oos), ("Gesamt", full)]:
            print(f"   {lab:26s} Trades {s['n']:4d} | Treffer {s['win']:.0%} | PF {s['pf']:.2f} | Rendite {s['ret']:+.1%} | CAGR {s['cagr']:+.1%} | max DD {s['dd']:.1%} | Ø/Trade {s['avg']:+.2%}")
        print(f"   schlechtester Monat {full['worst']:+.1%} ({full['worst_m']})")
        print("   Regime: " + " | ".join(f"{k} {v['n']} Tr, Beitrag {v['sum']:+.1%}, PF {v['pf']:.2f}" for k, v in reg.items()))
        print("   je Coin: " + " | ".join(f"{c} {len(g)} Tr PF {g.r[g.r>0].sum()/max(-g.r[g.r<0].sum(),1e-9):.2f}" for c, g in t.groupby("coin")))
        yr = (1 + R).groupby(R.index.year).prod() - 1
        print("   je Jahr: " + " | ".join(f"{y} {v:+.0%}" for y, v in yr.items()))
        print(f"   Score {sc}/25 {parts} -> {'BEHALTEN' if keep else 'verworfen'}")
        top = sorted(rows, key=lambda x: -min(x[3]['pf'], 10))[:3]
        print("   Top-3 im Gitter nach Gesamt-PF (Overfitting-Blick, NICHT gewaehlt): " +
              " ; ".join(f"{x[0]} PF {x[3]['pf']:.2f} OOS {x[2]['pf']:.2f} n {x[3]['n']}" for x in top))
        sys.stdout.flush()

    print("\n=== Rangliste ===")
    for name, p, sc, keep in sorted(results, key=lambda x: -x[2]):
        print(f"{sc:2d}/25 {'BEHALTEN ' if keep else 'verworfen'} {name} {p}")


if __name__ == "__main__":
    main()
