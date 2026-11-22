import glob
import time
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="東証全銘柄スクリーナー", layout="wide")
st.title("📱 東証全銘柄カスタムスクリーナー")


# GitHubリポジトリ内のExcel/CSVファイルを自動検索して読み込む
@st.cache_data
def get_jpx_tickers():
    files = glob.glob("*.xls*") + glob.glob("*.csv")
    if not files:
        st.warning("GitHubにExcelまたはCSVファイルが見つかりません。")
        return pd.DataFrame()
    target_file = next(iter(files))
    try:
        if target_file.endswith(".csv"):
            df = pd.read_csv(target_file)
        elif target_file.endswith(".xlsx"):
            df = pd.read_excel(target_file, engine="openpyxl")
        else:
            df = pd.read_excel(target_file, engine="xlrd")

        df.columns = df.columns.astype(str).str.strip()
        df["コード"] = (
            df["コード"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

        cols = ["コード", "銘柄名", "市場・商品区分"]
        for c in cols:
            if c not in df.columns:
                st.error(f"ファイル内に必要な列 '{c}' が見つかりません: {list(df.columns)}")
                return pd.DataFrame()

        return df[cols].dropna(subset=["コード"]).drop_duplicates(subset=["コード"])
    except Exception as e:
        st.error(f"ファイル（{target_file}）の読み込みに失敗しました: {e}")
        return pd.DataFrame()


# 東証の制限値幅テーブル
def get_price_limit(base_price):
    limits = [
        (100, 30), (200, 50), (500, 80), (700, 100), (1000, 150),
        (1500, 300), (2000, 400), (3000, 500), (5000, 700), (7000, 1000),
        (10000, 1500), (15000, 3000), (20000, 4000), (30000, 5000),
        (50000, 7000), (70000, 10000), (100000, 15000), (150000, 30000),
        (200000, 40000), (300000, 50000), (500000, 70000), (700000, 100000),
        (1000000, 150000), (1500000, 300000), (2000000, 400000), (3000000, 500000),
        (5000000, 700000), (7000000, 1000000), (10000000, 1500000), (15000000, 3000000),
        (20000000, 4000000), (30000000, 5000000), (50000000, 7000000)
    ]
    for price, limit in limits:
        if base_price < price:
            return limit
    return 10000000


jpx_df = get_jpx_tickers()

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
    with col2:
        direction = st.selectbox("モード切替", ["上昇パターン (+)", "下落パターン (-)"])

    is_up = "上昇" in direction
    sign = "+" if is_up else "-"
    s_label = "S高" if is_up else "S安"
    gap_label_a = "GDスタート＆2日前比" if is_up else "GUスタート＆2日前比"
    gap_label_b = "GDスタート＆前日比" if is_up else "GUスタート＆前日比"

    st.markdown("---")
    st.markdown("**判定条件：『グループA』 かつ 『グループB』 （各グループ内は『①必須(AND)』かつ『②〜⑤いずれか(OR)』）**")

    g_col1, g_col2 = st.columns(2)

    # 🅰️ グループA（1日前の動き）
    with g_col1:
        st.info("🅰️ **グループA（1日前：①AND かつ ②〜⑤OR）**")

        a_turn_chk = st.checkbox("① 【必須】1日前売買代金 (億円以上)", value=False)
        a_turn_oku = st.number_input("①の基準売買代金 (億円)", min_value=0.0, value=5.0, step=1.0, key="a_turn")

        st.markdown("---")
        a1_chk = st.checkbox(f"② 2日前引け比 1日前 ({sign}%以上)", value=False)
        pct_a1_input = st.number_input("②の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_a1")

        st.write("")
        a2_chk = st.checkbox(f"③ 1日前 寄り比 ({sign}%以上)", value=False)
        pct_a2_input = st.number_input("③の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_a2")

        st.write("")
        a3_chk = st.checkbox(f"④ 1日前 {gap_label_a} ({sign}%以上)", value=False)
        pct_a3_input = st.number_input("④の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_a3")

        st.write("")
        a4_chk = st.checkbox(f"⑤ 1日前 {s_label}", value=False)

    # 🅱️ グループB（当日の動き）
    with g_col2:
        st.success("🅱️ **グループB（当日：①AND かつ ②〜⑤OR）**")

        b_turn_chk = st.checkbox("① 【必須】当日売買代金 (億円以上)", value=False)
        b_turn_oku = st.number_input("①の基準売買代金 (億円)", min_value=0.0, value=5.0, step=1.0, key="b_turn")

        st.markdown("---")
        b1_chk = st.checkbox(f"② 1日前引け比 当日 ({sign}%以上)", value=True)
        pct_b1_input = st.number_input("②の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_b1")

        st.write("")
        b2_chk = st.checkbox(f"③ 当日 寄り比 ({sign}%以上)", value=True)
        pct_b2_input = st.number_input("③の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_b2")

        st.write("")
        b3_chk = st.checkbox(f"④ 当日 {gap_label_b} ({sign}%以上)", value=True)
        pct_b3_input = st.number_input("④の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_b3")

        st.write("")
        b4_chk = st.checkbox(f"⑤ 当日 {s_label}", value=True)

target_df = pd.DataFrame()
if not jpx_df.empty:
    m_col = "市場・商品区分"
    if market_option == "東証全株式（プライム・スタンダード・グロース）":
        target_df = jpx_df[jpx_df[m_col].str.contains("プライム|スタンダード|グロース", na=False)]
    elif market_option == "プライム（内国株式）のみ":
        target_df = jpx_df[jpx_df[m_col].str.contains("プライム", na=False)]
    elif market_option == "スタンダード（内国株式）のみ":
        target_df = jpx_df[jpx_df[m_col].str.contains("スタンダード", na=False)]
    elif market_option == "グロース（内国株式）のみ":
        target_df = jpx_df[jpx_df[m_col].str.contains("グロース", na=False)]
    else:
        target_df = jpx_df
    st.caption(f"現在のスキャン対象：{len(target_df):,} 銘柄")

if st.button("🚀 東証全銘柄から一括スクリーニング開始", type="primary", use_container_width=True):
    if target_df.empty:
        st.warning("対象銘柄が0件です。")
        st.stop()

    flags_a = [a_turn_chk, a1_chk, a2_chk, a3_chk, a4_chk]
    flags_b = [b_turn_chk, b1_chk, b2_chk, b3_chk, b4_chk]
    use_a = any(flags_a)
    use_b = any(flags_b)

    if not use_a and not use_b:
        st.warning("グループAまたはグループBの条件を少なくとも1つチェックしてください。")
        st.stop()

    code_to_name = dict(zip(target_df["コード"], target_df["銘柄名"]))
    code_to_market = dict(zip(target_df["コード"], target_df["市場・商品区分"]))
    codes = target_df["コード"].tolist()

    pct_a1, pct_a2, pct_a3 = pct_a1_input / 100.0, pct_a2_input / 100.0, pct_a3_input / 100.0
    pct_b1, pct_b2, pct_b3 = pct_b1_input / 100.0, pct_b2_input / 100.0, pct_b3_input / 100.0

    min_turn_a = a_turn_oku * 100_000_000
    min_turn_b = b_turn_oku * 100_000_000
    hits = []

    batch_size = 50
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
            progress_bar.progress((b_idx + 1) / total_batches)
            continue

        for code in batch_codes:
            ticker_str = f"{code}.T"
            try:
                if len(batch_codes) == 1:
                    df = data.dropna(how="all")
                else:
                    if not isinstance(data.columns, pd.MultiIndex) or ticker_str not in data.columns.get_level_values(0):
                        continue
                    df = data[ticker_str].dropna(how="all")

                if len(df) < 3 or not all(c in df.columns for c in ["Open", "Close", "Volume"]):
                    continue

                c2 = float(df["Close"].iloc[-3])
                o1, c1, v1 = float(df["Open"].iloc[-2]), float(df["Close"].iloc[-2]), float(df["Volume"].iloc[-2])
                o0, c0, v0 = float(df["Open"].iloc[-1]), float(df["Close"].iloc[-1]), float(df["Volume"].iloc[-1])

                if min(c2, o1, c1, o0, c0) <= 0:
                    continue

                turn1 = c1 * v1  # 1日前売買代金
                turn0 = c0 * v0  # 当日売買代金

                limit1 = get_price_limit(c2)
                limit0 = get_price_limit(c1)

                if is_up:
                    # グループA（1日前）
                    res_a = [
                        turn1 >= min_turn_a,
                        (c1 - c2) / c2 >= pct_a1,
                        (c1 - o1) / o1 >= pct_a2,
                        (o1 < c2) and ((c1 - c2) / c2 >= pct_a3),
                        c1 >= c2 + limit1,
                    ]
                    names_a = [
                        f"①1日前売買代金({a_turn_oku}億)",
                        f"②2日前比({pct_a1_input}%)",
                        f"③1日前寄り比({pct_a2_input}%)",
                        f"④1日前GD反発({pct_a3_input}%)",
                        "⑤S高",
                    ]
                    # グループB（当日）
                    res_b = [
                        turn0 >= min_turn_b,
                        (c0 - c1) / c1 >= pct_b1,
                        (c0 - o0) / o0 >= pct_b2,
                        (o0 < c1) and ((c0 - c1) / c1 >= pct_b3),
                        c0 >= c1 + limit0,
                    ]
                    names_b = [
                        f"①当日売買代金({b_turn_oku}億)",
                        f"②1日前比({pct_b1_input}%)",
                        f"③当日寄り比({pct_b2_input}%)",
                        f"④GD反発({pct_b3_input}%)",
                        "⑤当日S高",
                    ]
                else:
                    # グループA（1日前）
                    res_a = [
                        turn1 >= min_turn_a,
                        (c1 - c2) / c2 <= -pct_a1,
                        (c1 - o1) / o1 <= -pct_a2,
                        (o1 > c2) and ((c1 - c2) / c2 <= -pct_a3),
                        c1 <= c2 - limit1,
                    ]
                    names_a = [
