import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

# CSSで横並びのパーツがズレないよう微調整
st.markdown("""
    <style>
    .stButton button { border-radius: 5px; width: 100%; }
    [data-testid="stSidebar"] { display: none; }
    .main .block-container { padding-top: 1.5rem; max-width: 1100px; }
    hr { margin: 0.5rem 0; }
    /* 入力欄の高さをボタンに合わせる */
    div[data-testid="stTextInput"] > div > div > input { height: 45px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df_books = conn.read(worksheet="booklist", ttl=300)
        df_books.columns = df_books.columns.str.strip()
        df_votes = conn.read(worksheet="votes", ttl=300)
        if df_votes.empty:
            df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        df_votes.columns = df_votes.columns.str.strip()
        return df_books, df_votes
    except:
        return pd.DataFrame(), pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])

def save_votes(df):
    try:
        with st.spinner("反映中..."):
            conn.update(worksheet="votes", data=df)
            st.cache_data.clear()
            time.sleep(1.2) 
            st.rerun()
    except:
        st.error("保存失敗。再試行してください。")

df_books, df_votes = load_data()

tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- 【1】Bookリスト画面（1行集約版） ---
with tab_list:
    st.header("候補に登録")
    if not df_books.empty:
        all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
        selected_cat = st.selectbox("カテゴリ表示", all_cats)
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.subheader(f"📂 {cat_name}")
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            
            # ヘッダー代わりのラベル
            h_c1, h_c2, h_c3, h_c4 = st.columns([3, 1, 2, 1])
            h_c1.caption("書籍名 / 著者")
            h_c2.caption("詳細")
            h_c3.caption("あなたの名前")
            h_c4.caption("登録")
            st.markdown("---")

            for _, row in cat_books.iterrows():
                title = row.get("書籍名", "無題")
                author = row.get("著者名", "不明")
                url = row.get("URL")
                
                # 1行のレイアウト
                c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
                
                with c1:
                    st.markdown(f"**{title}** \n<small>{author}</small>", unsafe_allow_html=True)
                
                with c2:
                    if pd.notnull(url) and str(url).startswith("http"):
                        st.link_button("🔗 詳細", str(url))
                    else:
                        st.write("-")
                
                with c3:
                    # 各行で独立した名前入力
                    name_input = st.text_input("名前", key=f"name_in_{title}", label_visibility="collapsed")
                
                with c4:
                    if st.button("選ぶ", key=f"btn_{title}"):
                        if name_input:
                            new_row = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": name_input, "ポイント": 0}])
                            save_votes(pd.concat([df_votes, new_row], ignore_index=True))
                        else:
                            st.toast("名前を入力してください！")
                
                st.markdown("<hr style='border:0.1px solid #f0f2f6'>", unsafe_allow_html=True)

# --- 【2】投票・集計画面（変更なし） ---
with tab_vote:
    st.subheader("👤 ユーザー設定")
    my_name = st.text_input("あなたの名前を入力してください", key="my_login_name")

    admin_col1, admin_col2 = st.columns(2)
    with admin_col1:
        if st.button("全得点リセット"):
            save_votes(df_votes[df_votes["アクション"] == "選出"])
    with admin_col2:
        if st.button("全データ消去", type="primary"):
            save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))

    st.divider()

    if not df_votes.empty:
        df_v = df_votes.copy()
        df_v["ポイント"] = pd.to_numeric(df_v["ポイント"], errors='coerce').fillna(0)
        summary = df_v.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.subheader("🏆 ランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)

    st.divider()

    if not my_name:
        st.info("名前を入力すると投票機能が有効になります。")
    else:
        my_v_data = df_votes[(df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "
