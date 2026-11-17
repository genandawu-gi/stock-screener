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
        direction = st.selectbox("⑥ モード切替", ["上昇パターン (+)", "下落パターン (-)"])
        min_turn_oku = st.number_input("⑦ 1日前売買代金 (億円以上)", min_value=0.0, value=5.0, step=1.0)

    is_up = "上昇" in direction
    sign = "+" if is_up else "-"
    s_label = "S高" if is_up else "S安"
    gap_label = "GDスタート＆前日比" if is_up else "GUスタート＆前日比"

    st.markdown("---")
    st.markdown("**判定条件：『グループA（いずれか1つ）』 かつ 『グループB（いずれか1つ）』**")
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.info("🅰️ **グループA（1日前の動き：OR条件）**")
        
        c1_chk = st.checkbox(f"① 2日前引け比 1日前 ({sign}%以上)", value=True)
        pct1_input = st.number_input("①の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=10.0, step=0.5, key="pct1")
        
        st.write("") # 余白
        c2_chk = st.checkbox(f"② 1日前 寄り比 ({sign}%以上)", value=True)
        pct2_input = st.number_input("②の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=10.0, step=0.5, key="pct2")
        
        st.write("") # 余白
        c3_chk = st.checkbox(f"③ 1日前 {s_label}", value=True)

    with g_col2:
        st.success("🅱️ **グループB（当日の動き：OR条件）**")
        
        c4_chk = st.checkbox(f"④ 当日 寄り比 ({sign}%以上)", value=True)
        pct4_input = st.number_input("④の基準騰落率 (%)", min_value=0.1, max_value=100.0, value=8.0, step=0.5, key="pct4")
        
        st.write("") # 余白
        c5_chk = st.checkbox(f"⑤ 当日 {gap_label} ({sign}%以上)", value=True)
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

if st.button("🚀 東証全銘柄から一括スクリーニング開始", type="primary", use_container_width=True):
    if target_df.empty:
        st.warning("対象銘柄が0件です。")
        st.stop()

    flags_a = [c1_chk, c2_chk, c3_chk]
    flags_b = [c4_chk, c5_chk]

    if not any(flags_a) or not any(flags_b):
        st.warning("グループA（①〜③）とグループB（④〜⑤）のそれぞれで、最低1つ以上の条件にチェックを入れてください。")
        st.stop()

    code_to_name = dict(zip(target_df["コード"], target_df["銘柄名"]))
    code_to_market = dict(zip(target_df["コード"], target_df["市場・商品区分"]))
    codes = target_df["コード"].tolist()
    
    # 個別の騰落率を小数に変換
    pct1 = pct1_input / 100.0
    pct2 = pct2_input / 100.0
    pct4 = pct4_input / 100.0
    pct5 = pct5_input / 100.0
    
    min_turnover = min_turn_oku * 100_000_000
    is_up = "上昇" in direction
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

                if is_up:
                    res_a = [
                        (c1 - c2) / c2 >= pct1,
                        (c1 - o1) / o1 >= pct2,
                        c1 >= c2 + limit1
                    ]
                    names_a = [f"①2日前比({pct1_input}%)", f"②1日前寄り比({pct2_input}%)", "③S高"]

                    res_b = [
                        (c0 - o0) / o0 >= pct4,
                        (o0 < c1) and ((c0 - c1) / c1 >= pct5)
                    ]
                    names_b = [f"④当日寄り比({pct4_input}%)", f"⑤GD反発({pct5_input}%)"]
                else:
                    res_a = [
                        (c1 - c2) / c2 <= -pct1,
                        (c1 - o1) / o1 <= -pct2,
                        c1 <= c2 - limit1
                    ]
                    names_a = [f"①2日前比(-{pct1_input}%)", f"②1日前寄り比(-{pct2_input}%)", "③S安"]

                    res_b = [
                        (c0 - o0) / o0 <= -pct4,
                        (o0 > c1) and ((c0 - c1) / c1 <= -pct5)
                    ]
                    names_b = [f"④当日寄り比(-{pct4_input}%)", f"⑤GU失速(-{pct5_input}%)"]

                # グループA（OR）とグループB（OR）の評価
                eval_a = [r for r, flag in zip(res_a, flags_a) if flag]
                eval_b = [r for r, flag in zip(res_b, flags_b) if flag]

                # AとBを両方満たす（AND）場合のみ抽出
                if any(eval_a) and any(eval_b):
                    hit_tags_a = [n for r, flag, n in zip(res_a, flags_a, names_a) if r and flag]
                    hit_tags_b = [n for r, flag, n in zip(res_b, flags_b, names_b) if r and flag]
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
                        "該当条件(A)": " / ".join(hit_tags_a),
                        "該当条件(B)": " / ".join(hit_tags_b)
                    })
            except Exception:
                continue

        progress_bar.progress((b_idx + 1) / total_batches)
        time.sleep(0.1)

    status_text.empty()
    progress_bar.empty()

    st.subheader(f"抽出結果: {len(hits)} 件")
    if hits:
        st.dataframe(pd.DataFrame(hits), use_container_width=True, hide_index=True)
    else:
        st.info("条件に一致する銘柄はありませんでした。数値を緩めて再実行してください。")
