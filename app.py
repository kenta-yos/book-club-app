import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="読書会アプリ", layout="wide")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"初期設定エラー: {e}")
    st.stop()

def load_data():
    # Secretsの[connections.gsheets]から自動で読み込む設定です
    df_b = conn.read(worksheet="booklist", ttl=5)
    try:
        df_v = conn.read(worksheet="votes", ttl=0)
    except:
        df_v = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
    df_b.columns = df_b.columns.str.strip()
    return df_b, df_v

df_books, df_votes = load_data()

t1, t2 = st.tabs(["📖 リスト", "🗳️ 投票"])

with t1:
    for _, r in df_books.iterrows():
        title = r['書籍名']
        with st.expander(f"📔 {title}"):
            with st.form(f"f_{title}"):
                u = st.text_input("名前", key=f"u_{title}")
                if st.form_submit_button("候補に追加"):
                    if u:
                        new_row = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": u, "ポイント": 0}])
                        conn.update(worksheet="votes", data=pd.concat([df_votes, new_row]))
                        st.rerun()

with t2:
    if df_votes.empty:
        st.info("まだ候補がありません")
    else:
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.table(summary)
