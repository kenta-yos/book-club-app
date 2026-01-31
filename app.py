import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

st.markdown("""
    <style>
    .stButton button { border-radius: 5px; }
    [data-testid="stSidebar"] { display: none; }
    .main .block-container { padding-top: 1.5rem; max-width: 900px; }
    hr { margin: 0.8rem 0; }
    </style>
    """, unsafe_allow_html=True)

# 1. スプレッドシート接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. データ読み込み（APIエラー対策で少しキャッシュを持たせる：1秒）
def load_data():
    try:
        df_books = conn.read(worksheet="booklist", ttl=1)
        df_votes = conn.read(worksheet="votes", ttl=1)
        return df_books, df_votes
    except Exception as e:
        st.error("Googleとの接続でエラーが発生しました。少し待ってから再読み込みしてください。")
        return pd.DataFrame(), pd.DataFrame()

df_books, df_votes = load_data()

# 3. 書き込み用関数
def save_votes(df):
    conn.update(worksheet="votes", data=df)
    st.cache_data.clear()
    time.sleep(1) # API制限対策の待機
    st.rerun()

# ユーザー識別用（ブラウザを開いている間固定）
if "user_id" not in st.session_state:
    st.session_state.user_id = datetime.now().strftime("%H%M%S")

if "my_votes" not in st.session_state:
    st.session_state.my_votes = {}

# --- メイン画面 ---
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- 【1】Bookリスト画面 ---
with tab_list:
    st.header("読みたい本を候補に登録")
    if not df_books.empty:
        all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
        selected_cat = st.selectbox("カテゴリ表示切替", all_cats)
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.subheader(f"📂 {cat_name}")
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            for _, row in cat_books.iterrows():
                title = row.get("書籍名", "無題")
                with st.expander(f"📔 {title} / {row.get('著者名', '')}"):
                    with st.form(key=f"form_{title}"):
                        u_name = st.text_input("あなたの名前", key=f"name_{title}")
                        if st.form_submit_button("候補に選ぶ"):
                            if u_name:
                                new_row = pd.DataFrame([{"日時": datetime.now(), "アクション": "選出", "書籍タイトル": title, "ユーザー名": u_name, "ポイント": 0, "UID": st.session_state.user_id}])
                                save_votes(pd.concat([df_votes, new_row], ignore_index=True))

# --- 【2】投票・集計画面 ---
with tab_vote:
    header_col, action_col = st.columns([2, 3])
    with header_col:
        st.header("投票・集計")
    
    with action_col:
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("自分の投票をクリア"):
                # UIDが自分のもの、かつ「投票」アクションのみを削除
                if "UID" in df_votes.columns:
                    filtered_df = df_votes[~((df_votes["UID"] == st.session_state.user_id) & (df_votes["アクション"] == "投票"))]
                    st.session_state.my_votes = {}
                    save_votes(filtered_df)
        with c2:
            if st.button("得点リセット"):
                save_votes(df_votes[df_votes["アクション"] == "選出"])
        with c3:
            if st.button("全リセット", type="primary"):
                save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント", "UID"]))

    st.divider()
    
    if not df_votes.empty:
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.subheader("🏆 ランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)
    
    st.divider()
    
    nominated = df_votes[df_votes["アクション"] == "選出"]
    if nominated.empty:
        st.info("候補がありません。")
    else:
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            voted_p = st.session_state.my_votes.get(b_title, 0)
            
            r_col1, r_col2, r_col3 = st.columns([3, 0.6, 0.6])
            r_col1.markdown(f"**{b_title}** <small>({n_row['ユーザー名']}さん選出)</small>", unsafe_allow_html=True)
            
            # 投票済みなら無効化、未投票なら有効
            disabled = voted_p > 0
            if r_col2.button(f"+1", key=f"v1_{b_title}", type="primary" if voted_p==1 else "secondary", disabled=disabled):
                new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 1, "UID": st.session_state.user_id}])
                st.session_state.my_votes[b_title] = 1
                save_votes(pd.concat([df_votes, new_v], ignore_index=True))
            
            if r_col3.button(f"+2", key=f"v2_{b_title}", type="primary" if voted_p==2 else "secondary", disabled=disabled):
                new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 2, "UID": st.session_state.user_id}])
                st.session_state.my_votes[b_title] = 2
                save_votes(pd.concat([df_votes, new_v], ignore_index=True))
            st.markdown("---")
