import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

# UIの改善（CSS）
st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 5px; }
    .stTabs [data-baseweb="tab-list"] { position: sticky; top: 0; z-index: 999; background: white; }
    </style>
    """, unsafe_allow_html=True)

# API・接続設定
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- データ読み込み ---
def load_data():
    df_books = conn.read(worksheet="booklist", ttl=5)
    try:
        df_votes = conn.read(worksheet="votes", ttl=0)
    except:
        df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
    df_books.columns = df_books.columns.str.strip()
    return df_books, df_votes

df_books, df_votes = load_data()

# --- メイン画面 ---
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- AIサイドバー ---
with st.sidebar:
    st.subheader("🤖 AIコンシェルジュ")
    user_q = st.text_input("本探しをお手伝いします")
    if user_q:
        context = df_books[['書籍名', '著者名', 'カテゴリ']].to_string()
        prompt = f"リスト内の本だけで簡潔に回答して下さい。\n\n{context}\n\n質問：{user_q}"
        st.info(model.generate_content(prompt).text)

# --- 【1】Bookリスト ---
with tab_list:
    st.header("候補を選んでください")
    all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
    selected_cat = st.selectbox("カテゴリ絞り込み", all_cats)
    display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

    for _, row in display_df.iterrows():
        title = row['書籍名']
        with st.expander(f"📔 {title} / {row['著者名']}"):
            st.write(f"カテゴリ: {row['カテゴリ']}")
            if pd.notnull(row['URL']): st.link_button("詳細を見る", str(row['URL']))
            
            with st.form(key=f"f_{title}"):
                u_name = st.text_input("あなたの名前", key=f"n_{title}")
                if st.form_submit_button("この本を選出候補に入れる"):
                    if u_name:
                        new_data = {
                            "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "アクション": "選出",
                            "書籍
