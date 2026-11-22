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
        min_turn_oku = st.number_input("当日売買代金 (億円以上)", min_value=0.0, value=5.0, step=1.0)

    is_up = "上昇" in direction
    sign = "+" if is_up else "-"
    s_label = "S高" if is_up else "S安"
    gap_label = "GDスタート＆前日比" if is_up else "GUスタート＆前日比"

    st.markdown("---")
    st.markdown("**判定条件：『グループA（いずれか1つ）』 かつ 『グループB（いずれか1つ）』**")

    g_col1, g_col2 = st.columns(2)

    # 🅰️ グループA（1日前の動き）
    with g_col1:
        st.info("🅰️ **グループA（1日前の動き：OR条件）**")

        a_turn_chk = st.checkbox("① 1日前売買代金 (億円以上)", value=False)
        a_turn_oku = st.number_input("①の基準売買代金 (億円)", min_value=0.0, value=5.0, step=1.0, key="a_turn")

        st.write("")
        a1_chk = st.checkbox(f"② 2日前引け比 1日前 ({sign}%以上)", value=False)
        pct_a1_input = st.number_input("②の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_a1")

        st.write("")
        a2_chk = st.checkbox(f"③ 1日前 寄り比 ({sign}%以上)", value=False)
        pct_a2_input = st.number_input("③の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_a2")

        st.write("")
        a3_chk = st.checkbox(f"④ 1日前 {s_label}", value=False)

    # 🅱️ グループB（当日の動き）
    with g_col2:
        st.success("🅱️ **グループB（当日の動き：OR条件）**")

        b1_chk = st.checkbox(f"① 1日前引け比 当日 ({sign}%以上)", value=True)
        pct_b1_input = st.number_input("①の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_b1")

        st.write("")
        b2_chk = st.checkbox(f"② 当日 寄り比 ({sign}%以上)", value=True)
        pct_b2_input = st.number_input("②の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_b2")

        st.write("")
        b3_chk = st.checkbox(f"③ 当日 {gap_label} ({sign}%以上)", value=False)
        pct_b3_input = st.number_input("③の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct_b3")

        st.write("")
        b4_chk = st.checkbox(f"④ 当日 {s_label}", value=True)
