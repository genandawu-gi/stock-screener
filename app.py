import streamlit as st
import yfinance as yf
import pandas as pd
import glob
import time
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="東証全銘柄スクリーナー", layout="wide")
st.title("📱 東証全銘柄カスタムスクリーナー")

# 日本時間の現在時刻を取得し、16時基準で判定する関数
def get_jst_status():
    now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))
    is_after_16 = now_jst.hour >= 16
    return now_jst, is_after_16

# GitHubリポジトリ内のExcel/CSVファイルを自動検索して読み込む
@st.cache_data
def get_jpx_tickers():
    files = glob.glob("*.xls*") + glob.glob("*.csv")
    if not files:
        st.warning("ディレクトリ内にExcelまたはCSVファイルが見つかりません。")
        return pd.DataFrame()
    target_file = files[0]
    try:
        if target_file.endswith(".csv"):
            df = pd.read_csv(target_file)
        elif target_file.endswith(".xlsx"):
            df = pd.read_excel(target_file, engine="openpyxl")
        else:
            df = pd.read_excel(target_file, engine="xlrd")
        
        df.columns = df.columns.str.strip()
        df["コード"] = df["コード"].astype(str).str.strip().str.replace(".0", "", regex=False)
        
        cols = ["コード", "銘柄名", "市場・商品区分"]
        for c in cols:
            if c not in df.columns:
                st.error(f"ファイル内に必要な列 '{c}' が見つかりません: {list(df.columns)}")
                return pd.DataFrame()
                
        return df[cols]
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
now_jst, is_after_16 = get_jst_status()

# 現在の判定モードを画面上部に表示
if is_after_16:
    st.caption(f"🕒 現在時刻: {now_jst.strftime('%Y-%m-%d %H:%M')} (JST) ｜ **16時以降モード（Aグループ：当日確定値 vs 1日前）**")
else:
    st.caption(f"🕒 現在時刻: {now_jst.strftime('%Y-%m-%d %H:%M')} (JST) ｜ **16時前モード（前営業日確定値 vs 2営業日前）**")

with st.sidebar:
    st.header("🔍 スクリーニング条件")
    
    if not jpx_df.empty:
        markets = jpx_df["市場・商品区分"].unique().tolist()
        default_markets = [m for m in markets if "内国株式" in m]
        selected_markets = st.multiselect(
            "対象市場", 
            options=markets, 
            default=default_markets if default_markets else markets[:1]
        )
    else:
        selected_markets = []

    st.subheader("価格・出来高条件")
    col1, col2 = st.columns(2)
    with col1:
        min_price = st.number_input("最低株価 (円)", min_value=0, value=100, step=50)
    with col2:
        max_price = st.number_input("最高株価 (円)", min_value=0, value=5000, step=100)
        
    min_volume = st.number_input("最低出来高 (株)", min_value=0, value=100000, step=10000)
    min_change_pct = st.number_input("前日比上昇率 (%以上)", value=3.0, step=0.5)
    only_limit_up = st.checkbox("ストップ高銘柄のみ抽出", value=False)
    
    st.divider()
    max_scan = st.number_input("最大スキャン銘柄数 (テスト用)", min_value=10, max_value=5000, value=200, step=50)
    run_btn = st.button("🚀 スクリーニング実行", type="primary", use_container_width=True)

if run_btn:
    if jpx_df.empty:
        st.error("銘柄リストが読み込まれていません。")
    elif not selected_markets:
        st.warning("対象市場を1つ以上選択してください。")
    else:
        target_df = jpx_df[jpx_df["市場・商品区分"].isin(selected_markets)].head(max_scan)
        tickers = [f"{code}.T" for code in target_df["コード"]]
        
        st.info(f"対象銘柄数: {len(tickers)} 件のデータを取得中...")
        progress_bar = st.progress(0)
        results = []
        
        chunk_size = 100
        total_chunks = (len(tickers) + chunk_size - 1) // chunk_size
        today_date = now_jst.date()
        
        for i in range(total_chunks):
            chunk_tickers = tickers[i * chunk_size : (i + 1) * chunk_size]
            try:
                data = yf.download(chunk_tickers, period="7d", group_by="ticker", progress=False, threads=True)
                
                for code, name, market in zip(
                    target_df["コード"].iloc[i * chunk_size : (i + 1) * chunk_size],
                    target_df["銘柄名"].iloc[i * chunk_size : (i + 1) * chunk_size],
                    target_df["市場・商品区分"].iloc[i * chunk_size : (i + 1) * chunk_size]
                ):
                    ticker_sym = f"{code}.T"
                    if len(chunk_tickers) == 1:
                        df_t = data
                    else:
                        if ticker_sym not in data.columns.levels[0]:
                            continue
                        df_t = data[ticker_sym]
                    
                    df_t = df_t.dropna(subset=["Close"])
                    if df_t.empty:
                        continue
                    
                    # 16時前の場合、最新行が「今日（まだ16時を迎えていない未確定日）」であれば除外して1日ずらす
                    last_bar_date = df_t.index[-1].date()
                    if not is_after_16 and last_bar_date >= today_date:
                        df_t = df_t.iloc[:-1]
                        
                    if len(df_t) < 2:
                        continue
                        
                    # Aグループ（16時以降）: iloc[-1]が当日、iloc[-2]が1日前（前日）
                    # 16時前: 上記で当日行を除外しているため、iloc[-1]が1日前、iloc[-2]が2日前
                    prev_close = float(df_t["Close"].iloc[-2])
                    curr_close = float(df_t["Close"].iloc[-1])
                    curr_volume = int(df_t["Volume"].iloc[-1])
                    target_date_str = df_t.index[-1].strftime("%Y-%m-%d")
                    
                    change = curr_close - prev_close
                    change_pct = (change / prev_close) * 100
                    
                    # 制限値幅・ストップ高判定
                    limit_width = get_price_limit(prev_close)
                    is_limit_up = (curr_close >= prev_close + limit_width)
                    
                    # 条件フィルタリング
                    if not (min_price <= curr_close <= max_price):
                        continue
                    if curr_volume < min_volume:
                        continue
                    if change_pct < min_change_pct:
                        continue
                    if only_limit_up and not is_limit_up:
                        continue
                        
                    results.append({
                        "基準日": target_date_str,
                        "コード": code,
                        "銘柄名": name,
                        "市場": market,
                        "終値": round(curr_close, 1),
                        "前日比": round(change, 1),
                        "上昇率(%)": round(change_pct, 2),
                        "出来高": curr_volume,
                        "S高判定": "🔥 S高" if is_limit_up else "-"
                    })
            except Exception as e:
                st.warning(f"一部データの取得中にエラーが発生しました: {e}")
                
            progress_bar.progress((i + 1) / total_chunks)
            time.sleep(0.5)
            
        st.success(f"スキャン完了！ **{len(results)} 件** の銘柄がヒットしました。")
        
        if results:
            res_df = pd.DataFrame(results).sort_values(by="上昇率(%)", ascending=False)
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            csv = res_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 結果をCSVでダウンロード",
                data=csv,
                file_name=f"screener_results_{now_jst.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
