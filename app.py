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

# 2. データ読み込み関数
def load_data():
    try:
        df_books = conn.read(worksheet="booklist", ttl=1)
        df_books.columns = df_books.columns.str.strip()
        df_votes = conn.read(worksheet="votes", ttl=1)
        if df_votes.empty:
            df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        df_votes.columns = df_votes.columns.str.strip()
        return df_books, df_votes
    except:
        return pd.DataFrame(), pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])

df_books, df_votes = load_data()

# 3. 書き込み用関数
def save_votes(df):
    try:
        conn.update(worksheet="votes", data=df)
        st.cache_data.clear()
        time.sleep(1) 
        st.rerun()
    except:
        st.error("保存に失敗しました。時間をおいて再送してください。")

# --- メイン画面 ---
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- 【1】Bookリスト画面 ---
with tab_list:
    st.header("候補に登録")
    if not df_books.empty:
        all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
        selected_cat = st.selectbox("カテゴリ表示", all_cats)
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.subheader(f"📂 {cat_name}")
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            for _, row in cat_books.iterrows():
                title = row.get("書籍名", "無題")
                with st.expander(f"📔 {title}"):
                    with st.form(key=f"form_{title}"):
                        u_name = st.text_input("あなたの名前（必須）", key=f"n_{title}")
                        if st.form_submit_button("候補に選ぶ"):
                            if u_name:
                                new_row = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": u_name, "ポイント": 0}])
                                save_votes(pd.concat([df_votes, new_row], ignore_index=True))
                            else:
                                st.error("名前を入力してください")

# --- 【2】投票・集計画面 ---
with tab_vote:
    # ユーザー認証（名前で判定）
    st.subheader("👤 投票者ログイン")
    my_name = st.text_input("あなたの名前を入力してください（投票やクリアに使用）", key="my_login_name")

    # 管理用ボタン（名前不要）
    admin_col1, admin_col2 = st.columns(2)
    with admin_col1:
        if st.button("全得点リセット"):
            save_votes(df_votes[df_votes["アクション"] == "選出"])
    with admin_col2:
        if st.button("全データ消去", type="primary"):
            save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))

    st.divider()

    # ランキング
    if not df_votes.empty:
        df_v = df_votes.copy()
        df_v["ポイント"] = pd.to_numeric(df_v["ポイント"], errors='coerce').fillna(0)
        summary = df_v.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.subheader("🏆 ランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)

    st.divider()

    # 投票処理
    if not my_name:
        st.info("名前を入力すると投票・クリアができるようになります。")
    else:
        # 自分の今の投票状況をスキャン
        my_v_data = df_votes[(df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票")]
        voted_1_book = my_v_data[my_v_data["ポイント"].astype(float) == 1]["書籍タイトル"].tolist()
        voted_2_book = my_v_data[my_v_data["ポイント"].astype(float) == 2]["書籍タイトル"].tolist()
        
        has_voted_1 = len(voted_1_book) > 0
        has_voted_2 = len(voted_2_book) > 0

        # クリアボタン
        if st.button(f"{my_name}さんの投票をすべて取り消す"):
            # 自分かつ「投票」アクションの行を完全に削除
            filtered_df = df_votes[~((df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票"))]
            save_votes(filtered_df)

        st.subheader("🗳️ 投票エリア")
        nominated = df_votes[df_votes["アクション"] == "選出"]
        
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            
            # この本に自分が何点入れているか
            this_p = 0
            if b_title in voted_1_book: this_p = 1
            if b_title in voted_2_book: this_p = 2
            
            c1, c2, c3 = st.columns([3, 0.6, 0.6])
            c1.markdown(f"**{b_title}** <small>({n_row['ユーザー名']}さん選出)</small>", unsafe_allow_html=True)
            
            # +1ボタンの制御: すでにどこかで+1を使っている OR この本で+2を使っているなら無効
            d1 = has_voted_1 or (this_p == 2)
            if c2.button(f"+1", key=f"p1_{b_title}", type="primary" if this_p==1 else "secondary", disabled=d1):
                new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 1}])
                save_votes(pd.concat([df_votes, new_v], ignore_index=True))

            # +2ボタンの制御: すでにどこかで+2を使っている OR この本で+1を使っているなら無効
            d2 = has_voted_2 or (this_p == 1)
            if c3.button(f"+2", key=f"p2_{b_title}", type="primary" if this_p==2 else "secondary", disabled=d2):
                new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 2}])
                save_votes(pd.concat([df_votes, new_v], ignore_index=True))
            st.markdown("---")
