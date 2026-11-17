import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
import time

st.set_page_config(page_title="東証全銘柄スクリーナー", layout="wide")
st.title("📱 東証全銘柄カスタムスクリーナー")

# 海外サーバーからでも確実に取得できる東証上場銘柄一覧を取得（1日キャッシュ）
@st.cache_data(ttl=86400)
def get_jpx_tickers():
    urls = [
        "https://githubusercontent.com",
        "https://githubusercontent.com"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            df = pd.read_csv(io.BytesIO(res.content))
            if "コード" in df.columns and "銘柄名" in df.columns:
                df["コード"] = df["コード"].astype(str).str.strip()
                if "市場・商品区分" not in df.columns:
                    df["市場・商品区分"] = "東証上場"
                return df[["コード", "銘柄名", "市場・商品区分"]]
        except Exception:
            continue

    # 万が一外部CSVも取得できなかった場合の予備（東証主要・売買代金上位100銘柄リスト）
    fallback_codes = [
        ("7203", "トヨタ自動車", "プライム（内国株式）"), ("9984", "ソフトバンクグループ", "プライム（内国株式）"),
        ("6758", "ソニーグループ", "プライム（内国株式）"), ("8306", "三菱UFJフィナンシャルG", "プライム（内国株式）"),
        ("6857", "アドバンテスト", "プライム（内国株式）"), ("8035", "東京エレクトロン", "プライム（内国株式）"),
        ("6146", "ディスコ", "プライム（内国株式）"), ("6920", "レーザーテック", "プライム（内国株式）"),
        ("7011", "三菱重工業", "プライム（内国株式）"), ("7012", "川崎重工業", "プライム（内国株式）"),
        ("7013", "IHI", "プライム（内国株式）"), ("9101", "日本郵船", "プライム（内国株式）"),
        ("9104", "商船三井", "プライム（内国株式）"), ("9107", "川崎汽船", "プライム（内国株式）"),
        ("5803", "フジクラ", "プライム（内国株式）"), ("5801", "古河電気工業", "プライム（内国株式）"),
        ("5802", "住友電気工業", "プライム（内国株式）"), ("8316", "三井住友フィナンシャルG", "プライム（内国株式）"),
        ("8411", "みずほフィナンシャルG", "プライム（内国株式）"), ("8058", "三菱商事", "プライム（内国株式）"),
        ("8001", "伊藤忠商事", "プライム（内国株式）"), ("8031", "三井物産", "プライム（内国株式）"),
        ("9983", "ファーストリテイリング", "プライム（内国株式）"), ("6098", "リクルートHD", "プライム（内国株式）"),
        ("7974", "任天堂", "プライム（内国株式）"), ("4063", "信越化学工業", "プライム（内国株式）"),
        ("6501", "日立製作所", "プライム（内国株式）"), ("6702", "富士通", "プライム（内国株式）"),
        ("6701", "NEC", "プライム（内国株式）"), ("9432", "日本電信電話", "プライム（内国株式）"),
        ("9433", "KDDI", "プライム（内国株式）"), ("9434", "ソフトバンク", "プライム（内国株式）"),
        ("3778", "さくらインターネット", "プライム（内国株式）"), ("5253", "カバー", "グロース（内国株式）"),
        ("5595", "QPS研究所", "グロース（内国株式）"), ("9166", "GENDA", "グロース（内国株式）"),
        ("215A", "タイミー", "グロース（内国株式）"), ("4478", "フリー", "グロース（内国株式）"),
        ("4485", "JTOWER", "グロース（内国株式）"), ("7342", "ウェルスナビ", "グロース（内国株式）")
    ]
    st.warning("外部銘柄一覧に接続できなかったため、内蔵の主要銘柄リストを使用しています。")
    return pd.DataFrame(fallback_codes, columns=["コード", "銘柄名", "市場・商品区分"])

# 東証の制限値幅テーブル
def get_price_limit(base_price):
    limits = [
        (100, 30), (200, 50), (500, 80), (700, 100), (1000, 150),
        (1500, 300), (2000, 400), (3000, 500), (5000, 700), (7000, 1000),
        (10000, 1500), (15000, 3000), (20000, 4000), (30000, 5000),
        (50000, 7000), (70000, 10000), (100000, 15000), (150000, 30000),
        (200000, 40000), (300000, 50000), (500000, 70000), (700000, 100000),
        (1000000, 150000), (1500000, 300000), (2000000, 400000),
        (3000000, 500000), (5000000, 700000), (7000000, 1000000),
        (10000000, 1500000), (15000000, 3000000), (20000000, 4000000),
        (30000000, 5000000), (50000000, 7000000)
    ]
    for price, limit in limits:
        if base_price < price:
            return limit
    return 10000000

jpx_df = get_jpx_tickers()

# --- スマホで見やすい設定メニュー ---
with st.expander("⚙️ スクリーニング条件・対象市場", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        market_option = st.selectbox(
            "対象市場（全銘柄または市場別）",
            [
                "東証全株式（プライム・スタンダード・グロース）",
                "プライム（内国株式）のみ",
                "スタンダード（内国株式）のみ",
                "グロース（内国株式）のみ",
                "ETF・REIT含む全上場銘柄"
            ]
        )
        direction = st.selectbox("⑥ モード切替", ["上昇パターン (+)", "下落パターン (-)"])
    with col2:
        pct_input = st.number_input("基準騰落率 (%)", min_value=0.1, max_value=100.0, value=10.0, step=0.5)
        min_turn_oku = st.number_input("⑦ 1日前売買代金 (億円以上)", min_value=0.0, value=5.0, step=1.0)
        combine_logic = st.selectbox("①〜⑤の組み合わせ", ["いずれか1つ以上 (OR)", "すべて満たす (AND)"])

    st.write("**判定する条件を選択:**")
    sign = "+" if "上昇" in direction else "-"
    s_label = "S高" if "上昇" in direction else "S安"
    gap_label = "GDスタート＆前日比" if "上昇" in direction else "GUスタート＆前日比"

    c1_chk = st.checkbox(f"① 2日前引け比 1日前 {sign}{pct_input}%以上", value=True)
    c2_chk = st.checkbox(f"② 1日前 寄り比 {sign}{pct_input}%以上", value=True)
    c3_chk = st.checkbox(f"③ 1日前 {s_label}", value=True)
    c4_chk = st.checkbox(f"④ 当日 寄り比 {sign}{pct_input}%以上", value=True)
    c5_chk = st.checkbox(f"⑤ 当日 {gap_label} {sign}{pct_input}%以上", value=True)

# 対象銘柄の絞り込み
target_df = pd.DataFrame()
if not jpx_df.empty:
    if market_option == "東証全株式（プライム・スタンダード・グロース）":
        target_df = jpx_df[jpx_df["市場・商品区分"].str.contains("プライム|スタンダード|グロース", na=False)]
    elif market_option == "プライム（内国株式）のみ":
        target_df = jpx_df[jpx_df["市場・商品区分"].str.contains("プライム", na=False)]
    elif market_option == "スタンダード（内国株式）のみ":
        target_df = jpx_df[jpx_df["市場・商品区分"].str.contains("スタンダード", na=False)]
    elif market_option == "グロース（内国株式）のみ":
        target_df = jpx_df[jpx_df["市場・商品区分"].str.contains("グロース", na=False)]
    else:
        target_df = jpx_df

    st.caption(f"現在のスキャン対象：{len(target_df):,} 銘柄")

if st.button("🚀 東証全銘柄から一括スクリーニング開始", type="primary", use_container_width=True):
    if target_df.empty:
        st.warning("対象銘柄が0件です。市場区分を変更してください。")
        st.stop()

    code_to_name = dict(zip(target_df["コード"], target_df["銘柄名"]))
    code_to_market = dict(zip(target_df["コード"], target_df["市場・商品区分"]))
    codes = target_df["コード"].tolist()

    pct = pct_input / 100.0
    min_turnover = min_turn_oku * 100_000_000
    is_up = "上昇" in direction
    active_flags = [c1_chk, c2_chk, c3_chk, c4_chk, c5_chk]

    hits = []
    batch_size = 200
    total_batches = (len(codes) + batch_size - 1) // batch_size
    progress_bar = st.progress(0)
    status_text = st.empty()

    for b_idx in range(total_batches):
        batch_codes = codes[b_idx * batch_size : (b_idx + 1) * batch_size]
        yf_tickers = [f"{c}.T" for c in batch_codes]
        status_text.text(f"株価データ取得中... ({min((b_idx + 1) * batch_size, len(codes)):,} / {len(codes):,} 銘柄)")

        try:
            data = yf.download(yf_tickers, period="5d", group_by="ticker", progress=False, threads=True)
        except Exception:
            continue

        for code in batch_codes:
            ticker = f"{code}.T"
            try:
                df = data[ticker].dropna() if len(batch_codes) > 1 else data.dropna()
                if len(df) < 3:
                    continue

                c2 = float(df["Close"].iloc[-3])
                o1 = float(df["Open"].iloc[-2])
                c1 = float(df["Close"].iloc[-2])
                v1 = float(df["Volume"].iloc[-2])
                o0 = float(df["Open"].iloc[-1])
                c0 = float(df["Close"].iloc[-1])

                # ⑦ 1日前売買代金
                turn1 = c1 * v1
                if turn1 < min_turnover:
                    continue

                limit1 = get_price_limit(c2)

                if is_up:
                    res = [
                        (c1 - c2) / c2 >= pct,
                        (c1 - o1) / o1 >= pct,
                        c1 >= c2 + limit1,
                        (c0 - o0) / o0 >= pct,
                        (o0 < c1) and ((c0 - c1) / c1 >= pct)
                    ]
                    names = ["①2日前比", "②1日前寄り比", "③S高", "④当日寄り比", "⑤GD反発"]
                else:
                    res = [
                        (c1 - c2) / c2 <= -pct,
                        (c1 - o1) / o1 <= -pct,
                        c1 <= c2 - limit1,
                        (c0 - o0) / o0 <= -pct,
                        (o0 > c1) and ((c0 - c1) / c1 <= -pct)
                    ]
                    names = ["①2日前比", "②1日前寄り比", "③S安", "④当日寄り比", "⑤GU失速"]

                eval_res = [r for r, flag in zip(res, active_flags) if flag]
                if not eval_res:
                    continue

                matched = all(eval_res) if "AND" in combine_logic else any(eval_res)
                if matched:
                    hit_tags = [n for r, flag, n in zip(res, active_flags, names) if r and flag]
                    market_short = code_to_market.get(code, "").replace("（内国株式）", "")
                    hits.append({
                        "コード": code,
                        "銘柄名": code_to_name.get(code, ""),
                        "市場": market_short,
                        "2日前終値": f"{c2:,.0f}",
                        "1日前終値": f"{c1:,.0f} ({(c1-c2)/c2*100:+.1f}%)",
                        "1日前売買代金": f"{turn1/100_000_000:.1f}億円",
                        "当日始値": f"{o0:,.0f}",
                        "当日現在値": f"{c0:,.0f} ({(c0-c1)/c1*100:+.1f}%)",
                        "該当条件": " / ".join(hit_tags)
                    })
            except Exception:
                continue

        progress_bar.progress((b_idx + 1) / total_batches)
        time.sleep(0.2)

    status_text.empty()
    progress_bar.empty()

    st.subheader(f"抽出結果: {len(hits)} 件")
    if hits:
        st.dataframe(pd.DataFrame(hits), use_container_width=True, hide_index=True)
    else:
        st.info("条件に一致する銘柄はありませんでした。数値を緩めて再実行してください。")
