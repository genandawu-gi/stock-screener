import streamlit as st
import yfinance as yf
import pandas as pd
import glob
import time

st.set_page_config(page_title="東証全銘柄スクリーナー", layout="wide")
st.title("📱 東証全銘柄カスタムスクリーナー")

# GitHubリポジトリ内のExcel/CSVファイルを自動検索して読み込む
@st.cache_data
def get_jpx_tickers():
    files = glob.glob("*.xls*") + glob.glob("*.csv")
    if not files:
        st.warning("GitHubにExcelまたはCSVファイルが見つかりません。")
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

with st.expander("⚙️ スクリーニング条件・対象市場（上昇・下落を同時抽出）", expanded=True):
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
        min_turn_oku = st.number_input("⑦ 1日前売買代金 (億円以上)", min_value=0.0, value=5.0, step=1.0)
        st.info("💡 1回のスキャンで「📈上昇パターン」と「📉下落パターン」の両方を同時に抽出します。")

    st.markdown("---")
    st.markdown("**判定条件：『グループA（いずれか1つ）』 かつ 『グループB（いずれか1つ）』**")
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.info("🅰️ **グループA（1日前の動き：OR条件）**")
        
        c1_chk = st.checkbox("① 2日前引け比 1日前 (±%以上)", value=True)
        pct1_input = st.number_input("①の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=10.0, step=0.5, key="pct1")
        
        st.write("")
        c2_chk = st.checkbox("② 1日前 寄り比 (±%以上)", value=True)
        pct2_input = st.number_input("②の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=10.0, step=0.5, key="pct2")
        
        st.write("")
        c3_chk = st.checkbox("③ 1日前 S高 / S安", value=True)

    with g_col2:
        st.success("🅱️ **グループB（当日の動き：OR条件）**")
        
        c4_chk = st.checkbox("④ 当日 寄り比 (±%以上)", value=True)
        pct4_input = st.number_input("④の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct4")
        
        st.write("")
        c5_chk = st.checkbox("⑤ 当日 GD反発 / GU失速 (±%以上)", value=True)
        pct5_input = st.number_input("⑤の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct5")

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

if st.button("🚀 東証全銘柄から一括スクリーニング開始（上昇・下落同時）", type="primary", use_container_width=True):
    if target_df.empty:
        st.warning("対象銘柄が0件です。")
        st.stop()

    flags_a = [c1_chk, c2_chk, c3_chk]
    flags_b = [c4_chk, c5_chk]
    use_a = any(flags_a)
    use_b = any(flags_b)

    code_to_name = dict(zip(target_df["コード"], target_df["銘柄名"]))
    code_to_market = dict(zip(target_df["コード"], target_df["市場・商品区分"]))
    codes = target_df["コード"].tolist()
    
    # 個別の騰落率を小数に変換
    pct1 = pct1_input / 100.0
    pct2 = pct2_input / 100.0
    pct4 = pct4_input / 100.0
    pct5 = pct5_input / 100.0
    
    min_turnover = min_turn_oku * 100_000_000
    hits_up = []
    hits_down = []
    
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
            continue

        for code in batch_codes:
            ticker_str = f"{code}.T"
            try:
                if len(batch_codes) == 1:
                    df = data.dropna(how="all")
                else:
                    if ticker_str not in data.columns.levels[0]:
                        continue
                    df = data[ticker_str].dropna(how="all")

                if len(df) < 3:
                    continue

                req_cols = ["Open", "Close", "Volume"]
                if not all(col in df.columns for col in req_cols):
                    continue

                c2 = float(df["Close"].iloc[-3])
                o1 = float(df["Open"].iloc[-2])
                c1 = float(df["Close"].iloc[-2])
                v1 = float(df["Volume"].iloc[-2])
                o0 = float(df["Open"].iloc[-1])
                c0 = float(df["Close"].iloc[-1])

                # ⑦ 1日前売買代金フィルター
                turn1 = c1 * v1
                if turn1 < min_turnover:
                    continue

                limit1 = get_price_limit(c2)
                market_short = code_to_market.get(code, "").replace("（内国株式）", "")

                def build_row(tags_a, tags_b):
                    return {
                        "コード": code,
                        "銘柄名": code_to_name.get(code, ""),
                        "市場": market_short,
                        "2日前終値": f"{c2:,.0f}",
                        "1日前終値": f"{c1:,.0f} ({(c1-c2)/c2*100:+.1f}%)",
                        "1日前売買代金": f"{turn1/100_000_000:.1f}億円",
                        "当日始値": f"{o0:,.0f}",
                        "当日現在値": f"{c0:,.0f} ({(c0-c1)/c1*100:+.1f}%)",
                        "該当条件(A)": " / ".join(tags_a) if tags_a else "指定なし",
                        "該当条件(B)": " / ".join(tags_b) if tags_b else "指定なし"
                    }

                # --- 1. 上昇パターンの判定 ---
                res_a_up = [
                    (c1 - c2) / c2 >= pct1,
                    (c1 - o1) / o1 >= pct2,
                    c1 >= c2 + limit1
                ]
                names_a_up = [f"①2日前比(+{pct1_input}%)", f"②1日前寄り比(+{pct2_input}%)", "③S高"]

                res_b_up = [
                    (c0 - o0) / o0 >= pct4,
                    (o0 < c1) and ((c0 - c1) / c1 >= pct5)
                ]
                names_b_up = [f"④当日寄り比(+{pct4_input}%)", f"⑤GD反発(+{pct5_input}%)"]

                match_a_up = any(r for r, f in zip(res_a_up, flags_a) if f) if use_a else True
                match_b_up = any(r for r, f in zip(res_b_up, flags_b) if f) if use_b else True

                if match_a_up and match_b_up:
                    t_a = [n for r, f, n in zip(res_a_up, flags_a, names_a_up) if r and f]
                    t_b = [n for r, f, n in zip(res_b_up, flags_b, names_b_up) if r and f]
                    hits_up.append(build_row(t_a, t_b))

                # --- 2. 下落パターンの判定 ---
                res_a_down = [
                    (c1 - c2) / c2 <= -pct1,
                    (c1 - o1) / o1 <= -pct2,
                    c1 <= c2 - limit1
                ]
                names_a_down = [f"①2日前比(-{pct1_input}%)", f"②1日前寄り比(-{pct2_input}%)", "③S安"]

                res_b_down = [
                    (c0 - o0) / o0 <= -pct4,
                    (o0 > c1) and ((c0 - c1) / c1 <= -pct5)
                ]
                names_b_down = [f"④当日寄り比(-{pct4_input}%)", f"⑤GU失速(-{pct5_input}%)"]

                match_a_down = any(r for r, f in zip(res_a_down, flags_a) if f) if use_a else True
                match_b_down = any(r for r, f in zip(res_b_down, flags_b) if f) if use_b else True

                if match_a_down and match_b_down:
                    t_a = [n for r, f, n in zip(res_a_down, flags_a, names_a_down) if r and f]
                    t_b = [n for r, f, n in zip(res_b_down, flags_b, names_b_down) if r and f]
                    hits_down.append(build_row(t_a, t_b))

            except Exception:
                continue

        progress_bar.progress((b_idx + 1) / total_batches)
        time.sleep(0.1)

    status_text.empty()
    progress_bar.empty()

    # --- 結果の同時表示 ---
    st.markdown("---")
    tab_up, tab_down = st.tabs([f"📈 上昇パターン ({len(hits_up)} 件)", f"📉 下落パターン ({len(hits_down)} 件)"])

    with tab_up:
