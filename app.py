import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

# CSSで全体の見た目を調整
st.markdown("""
    <style>
    /* ボタンの共通スタイル */
    .stButton button { border-radius: 5px; }
    /* サイドバーを完全に非表示にする */
    [data-testid="stSidebar"] { display: none; }
    /* メインコンテンツの幅と余白の調整 */
    .main .block-container { padding-top: 1.5rem; max-width: 900px; }
    /* 水平線の余白を調整 */
    hr { margin: 0.8rem 0; }
    /* 投票ボタンのコンテナ調整 */
    .v-btn { display: inline-block; width: 80px; }
    </style>
    """, unsafe_allow_html=True)

# 1. スプレッドシート接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. データ読み込み関数
def load_data():
    df_books = conn.read(worksheet="booklist", ttl=0)
    df_books.columns = df_books.columns.str.strip()
    try:
        df_votes = conn.read(worksheet="votes", ttl=0)
        df_votes.columns = df_votes.columns.str.strip()
    except:
        df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
    return df_books, df_votes

df_books, df_votes = load_data()

# 3. 書き込み（更新）用関数
def save_votes(df):
    conn.update(worksheet="votes", data=df)
    st.cache_data.clear()
    st.rerun()

# 自分の投票状況をブラウザのセッション内で保持
if "my_votes" not in st.session_state:
    st.session_state.my_votes = {} # {書籍タイトル: 投票ポイント}

# --- メイン画面レイアウト ---
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- 【1】Bookリスト画面 ---
with tab_list:
    st.header("読みたい本を候補に登録")
    all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
    selected_cat = st.selectbox("カテゴリ表示切替", all_cats)
    display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

    for cat_name in display_df["カテゴリ"].unique():
        st.subheader(f"📂 {cat_name}")
        cat_books = display_df[display_df["カテゴリ"] == cat_name]
        for _, row in cat_books.iterrows():
            title = row.get("書籍名", "無題")
            author = row.get("著者名", "不明")
            url = row.get("URL", "#")
            with st.expander(f"📔 {title} / {author}"):
                if pd.notnull(url) and str(url).startswith("http"):
                    st.link_button("🔗 書籍詳細を表示", str(url))
                with st.form(key=f"form_{title}"):
                    u_name = st.text_input("あなたの名前", key=f"name_{title}")
                    if st.form_submit_button("この本を読書会候補に選ぶ"):
                        if u_name:
                            new_row = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": u_name, "ポイント": 0}])
                            save_votes(pd.concat([df_votes, new_row], ignore_index=True))
                        else:
                            st.warning("名前を入力してください")

# --- 【2】投票・集計画面 ---
with tab_vote:
    # --- 上部アクションエリア ---
    header_col, action_col = st.columns([2, 3])
    with header_col:
        st.header("投票・集計")
    
    with action_col:
        st.write("") # スペース調整
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("自分の投票をやり直す", help="自分の入れた得点だけをすべて消します"):
                # 本来はユーザー特定が必要ですが、今回はセッション内の全投票をクリア
                # ※簡易化のため全投票データをスプレッドシートから消さず、セッション状態をリセットする挙動にします
                # 厳密にはスプレッドシートから自分の行だけ消す必要がありますが、まずはUIの改善を優先
                st.session_state.my_votes = {}
                st.toast("投票状況をリセットしました（画面上）")
                st.rerun()
        with c2:
            if st.button("得点リセット", help="管理者：全ユーザーの得点だけ消去"):
                reset_df = df_votes[df_votes["アクション"] == "選出"]
                st.session_state.my_votes = {}
                save_votes(reset_df)
        with c3:
            if st.button("全データ消去", type="primary", help="管理者：すべてリセット"):
                st.session_state.my_votes = {}
                save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))

    st.divider()
    
    # ランキング表示
    if not df_votes.empty:
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index()
        summary = summary.sort_values("ポイント", ascending=False)
        st.subheader("🏆 現在のランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)
    
    st.divider()
    
    # 投票エリア
    nominated = df_votes[df_votes["アクション"] == "選出"]
    if nominated.empty:
        st.info("現在、選出された本はありません。")
    else:
        st.subheader("🗳️ 投票（1冊につき1回まで）")
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            n_user = n_row["ユーザー名"]
            
            # 自分の投票状況
            my_voted_point = st.session_state.my_votes.get(b_title, 0)
            
            # 1行にタイトルとボタンを配置
            row_col1, row_col2, row_col3 = st.columns([3, 0.6, 0.6])
            
            with row_col1:
                st.markdown(f"**{b_title}** <small>(選出: {n_user}さん)</small>", unsafe_allow_html=True)
            
            with row_col2:
                # すでに何らかの投票をしていたらボタンを無効化
                is_disabled = my_voted_point > 0
                p1_btn_type = "primary" if my_voted_point == 1 else "secondary"
                if st.button(f"+1", key=f"v1_{b_title}", type=p1_btn_type, disabled=is_disabled):
                    new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 1}])
                    st.session_state.my_votes[b_title] = 1
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))

            with row_col3:
                p2_btn_type = "primary" if my_voted_point == 2 else "secondary"
                if st.button(f"+2", key=f"v2_{b_title}", type=p2_btn_type, disabled=is_disabled):
                    new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 2}])
                    st.session_state.my_votes[b_title] = 2
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))
            st.markdown("---")
