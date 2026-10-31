"""Baixa cotações (Yahoo Finance), calcula indicadores e gera JSONs para o site.

Uso:  python scripts/build.py [--limit N]
Saída: docs/data/index.json  +  docs/data/<TICKER>.json
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data"
BARS = 300          # candles exibidos no gráfico
HISTORY = "2y"      # histórico baixado (EMA200 precisa de aquecimento)
LIQ_DAYS = 60       # janela da liquidez (pregões, ~3 meses). Ajuste se quiser
BATCH = 25          # tickers por requisição
CROSS_DAYS = 3      # um cruzamento de médias vale se ocorreu nos últimos N pregões (1 = só no último)


def load_tickers():
    seen, out = set(), []
    for line in (ROOT / "tickers.txt").read_text().splitlines():
        line = line.split("#")[0]
        for t in line.split():
            t = t.strip().upper().replace(".SA", "")
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out


# ---------- indicadores ----------
def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()   # suavização de Wilder
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def macd(close, fast=12, slow=26, sig=9):
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    signal = line.ewm(span=sig, adjust=False).mean()
    return line, signal, line - signal


def slow_stoch(high, low, close, k=5, d=3):
    ll, hh = low.rolling(k).min(), high.rolling(k).max()
    fast_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    slow_k = fast_k.rolling(3).mean()
    return slow_k, slow_k.rolling(d).mean()


def atr(high, low, close, n=14):
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean()


def add_indicators(df):
    c, h, l = df["Close"], df["High"], df["Low"]
    df["MA9"] = c.rolling(9).mean()
    df["SMA20"] = c.rolling(20).mean()
    sd = c.rolling(20).std()
    df["BB_UP"] = df["SMA20"] + 2 * sd
    df["BB_LO"] = df["SMA20"] - 2 * sd
    df["EMA50"] = c.ewm(span=50, adjust=False).mean()
    df["EMA200"] = c.ewm(span=200, adjust=False).mean()
    df["RSI"] = rsi(c)
    df["MACD"], df["SIGNAL"], df["HIST"] = macd(c)
    df["STK"], df["STD"] = slow_stoch(h, l, c)
    df["ATR"] = atr(h, l, c)
    return df


def recent_cross(a, b, days=CROSS_DAYS):
    """Cruzamento mais recente de a sobre b nos últimos `days` pregões: 1 = a cruzou para cima, -1 = para baixo."""
    diff = (a - b).tail(days + 1).to_numpy()
    result = 0
    for prev, cur in zip(diff[:-1], diff[1:]):
        if np.isnan(prev) or np.isnan(cur):
            continue
        if prev <= 0 < cur:
            result = 1
        elif prev >= 0 > cur:
            result = -1
    return result


def series(df, col, nd=4):
    s = df[col]
    return [None if pd.isna(v) else round(float(v), nd) for v in s]


def download(batch):
    """Baixa um lote; tenta de novo com espera crescente se o Yahoo limitar/recusar."""
    raw = None
    for attempt in range(1, 5):
        try:
            raw = yf.download(
                [t + ".SA" for t in batch], period=HISTORY, interval="1d",
                group_by="ticker", auto_adjust=False, threads=False, progress=False,
            )
            if raw is not None and not raw.empty:
                break
            print(f"    tentativa {attempt}: resposta vazia")
        except Exception as e:  # noqa: BLE001
            print(f"    tentativa {attempt}: {type(e).__name__}: {str(e)[:150]}")
        time.sleep(10 * attempt)
    if raw is None or raw.empty:
        return {}
    res = {}
    for t in batch:
        try:
            sub = raw[t + ".SA"] if isinstance(raw.columns, pd.MultiIndex) else raw
            sub = sub.dropna(subset=["Close"])
            if len(sub):
                res[t] = sub[["Open", "High", "Low", "Close", "Volume"]].copy()
        except (KeyError, TypeError):
            pass  # ticker inexistente/deslistado
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="processa só os N primeiros (teste)")
    args = ap.parse_args()

    tickers = load_tickers()
    if args.limit:
        tickers = tickers[: args.limit]
    print(f"{len(tickers)} tickers na lista")

    frames = {}
    for i in range(0, len(tickers), BATCH):
        b = tickers[i : i + BATCH]
        print(f"lote {i // BATCH + 1}/{-(-len(tickers) // BATCH)}")
        frames.update(download(b))
        print(f"  baixados {len(frames)} válidos até agora")
        time.sleep(3)  # pausa entre lotes para não ser limitado

    # liquidez = média do volume financeiro (Close*Volume) nos últimos LIQ_DAYS pregões
    liq = {}
    for t, df in frames.items():
        tail = df.tail(LIQ_DAYS)
        liq[t] = float((tail["Close"] * tail["Volume"]).mean())
    ranking = sorted(liq, key=liq.get, reverse=True)
    rank = {t: i + 1 for i, t in enumerate(ranking)}

    if OUT.exists() and not OUT.is_dir():  # "data" foi enviado ao repositório como arquivo
        OUT.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()

    index = []
    for t in ranking:
        df = frames[t]
        if len(df) < 60:
            continue
        df = add_indicators(df.copy())
        last, prev = df.iloc[-1], df.iloc[-2]
        view = df.tail(BARS)
        payload = {
            "ticker": t,
            "rank": rank[t],
            "liq": liq[t],
            "t": [d.strftime("%Y-%m-%d") for d in view.index],
            "o": series(view, "Open", 2), "h": series(view, "High", 2),
            "l": series(view, "Low", 2), "c": series(view, "Close", 2),
            "v": [int(x) for x in view["Volume"]],
        }
        for key, col in [("ma9", "MA9"), ("sma20", "SMA20"), ("bbu", "BB_UP"), ("bbl", "BB_LO"),
                         ("ema50", "EMA50"), ("ema200", "EMA200"), ("rsi", "RSI"), ("macd", "MACD"),
                         ("sig", "SIGNAL"), ("hist", "HIST"), ("stk", "STK"), ("std", "STD"), ("atr", "ATR")]:
            payload[key] = series(view, col)
        (OUT / f"{t}.json").write_text(json.dumps(payload, separators=(",", ":")))

        def f(x, nd=2):
            return None if pd.isna(x) else round(float(x), nd)

        index.append({
            "t": t, "rank": rank[t], "liq": round(liq[t]),
            "close": f(last["Close"]), "chg": f((last["Close"] / prev["Close"] - 1) * 100),
            "rsi": f(last["RSI"]), "macd": f(last["MACD"], 3),
            "above200": bool(last["Close"] > last["EMA200"]) if not pd.isna(last["EMA200"]) else None,
            # cruzamentos nos últimos CROSS_DAYS pregões: 1 = para cima, -1 = para baixo, 0 = nenhum
            "cross": recent_cross(df["MA9"], df["SMA20"]),        # MA9 x SMA20
            "c2050": recent_cross(df["SMA20"], df["EMA50"]),      # SMA20 x EMA50
            "m9gt20": bool(last["MA9"] > last["SMA20"]) if not pd.isna(last["SMA20"]) else None,
            "date": df.index[-1].strftime("%Y-%m-%d"),
        })

    meta = {"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "count": len(index), "cross_days": CROSS_DAYS, "items": index}
    (OUT / "index.json").write_text(json.dumps(meta, separators=(",", ":")))
    print(f"OK: {len(index)} ativos gerados em {OUT}")
    if not index:
        sys.exit("Nenhum ativo gerado")


if __name__ == "__main__":
    main()
