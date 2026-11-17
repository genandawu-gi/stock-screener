import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="東証全銘柄スクリーナー", layout="wide")
st.title("📱 東証全銘柄カスタムスクリーナー")

# JPX公式サイトから最新の東証上場銘柄一覧を取得（1日キャッシュ）
@st.cache_data(ttl=86400)
def get_jpx_tickers():
    url = "https://jpx.co.jp"
    try:
        df = pd.read_excel(url)
        # 4桁の数字コード（普通株式等）を中心に整形
        df["コード"] = df["コード"].astype(str).str.strip()
        return df[["コード", "銘柄名", "市場・商品区分"]]
    except Exception as e:
        st.error(f"JPX銘柄一覧の取得に失敗しました: {e}")
        return pd.DataFrame()

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
if not jpx_df.empty:
    if market_option == "東証全株式（プライム・スタンダード・グロース）":
        target_df = jpx_df[jpx_df["市場・商品区分"].str.contains("プライム|スタンダード|グロース", na=False)]
    elif market_option == "プライム（内国株式）のみ":
        target_df = jpx_df[jpx_df["市場・商品区分"] == "プライム（内国株式）"]
    elif market_option == "スタンダード（内国株式）のみ":
        target_df = jpx_df[jpx_df["市場・商品区分"] == "スタンダード（内国株式）"]
    elif market_option == "グロース（内国株式）のみ":
        target_df = jpx_df[jpx_df["市場・商品区分"] == "グロース（内国株式）"]
    else:
        target_df = jpx_df

    st.caption(f"現在のスキャン対象：{len(target_df):,} 銘柄")

if st.button("🚀 東証全銘柄から一括スクリーニング開始", type="primary", use_container_width=True):
    if jpx_df.empty:
        st.stop()

    code_to_name = dict(zip(target_df["コード"], target_df["銘柄名"]))
    code_to_market = dict(zip(target_df["コード"], target_df["市場・商品区分"]))
    codes = target_df["コード"].tolist()

    pct = pct_input / 100.0
    min_turnover = min_turn_oku * 100_000_000
    is_up = "上昇" in direction
    active_flags = [c1_chk, c2_chk, c3_chk, c4_chk, c5_chk]

    hits = []
    batch_size = 200  # 200銘柄ずつ分割取得
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
