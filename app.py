import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="読書会アプリ", layout="wide")

# 1. 接続設定（Secretsから自動読み込み）
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"設定エラー: {e}")
    st.stop()

# 2. データ読み込み関数
def load_data():
    # Secretsの [connections.gsheets] を使うので、引数は不要
    df_b = conn.read(worksheet="booklist", ttl=5)
    try:
        df_v = conn.read(worksheet="votes", ttl=0)
    except:
        df_v = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
    df_b.columns = df_b.columns.str.strip()
    return df_b, df_v

df_books, df_votes = load_data()

# 3. 画面表示
t1, t2 = st.tabs(["📖 本を選ぶ", "🗳️ 投票結果"])

with st.sidebar:
    st.subheader("🤖 AI相談")
    q = st.text_input("どんな本が読みたい？")
    if q:
        res = model.generate_content(f"{df_books.to_string()}\n質問:{q}")
        st.info(res.text)

with t1:
    for _, r in df_books.iterrows():
        title = r['書籍名']
        with st.expander(f"📔 {title}"):
            st.write(f"著者: {r['著者名']} / カテゴリ: {r['カテゴリ']}")
            with st.form(f"f_{title}"):
                u = st.text_input("あなたの名前", key=f"u_{title}")
                if st.form_submit_button("候補に追加"):
                    if u:
                        new_row = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": u, "ポイント": 0}])
                        conn.update(worksheet="votes", data=pd.concat([df_votes, new_row]))
                        st.success("追加しました！")
                        st.rerun()

with t2:
    if df_votes.empty:
        st.info("まだ候補がありません")
    else:
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.table(summary)
        
        for t in df_votes[df_votes["アクション"] == "選出"]["書籍タイトル"].unique():
            st.write(f"--- {t} ---")
            c1, c2, c3 = st.columns(3)
            def vote(p):
                v = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d"), "アクション": "投票", "書籍タイトル": t, "ユーザー名": "匿名", "ポイント": p}])
                conn.update(worksheet="votes", data=pd.concat([df_votes, v]))
                st.rerun()
            if c1.button("+1", key=f"p_{t}"): vote(1)
            if c2.button("-1", key=f"m_{t}"): vote(-1)
            if c3.button("消去", key=f"d_{t}"):
                conn.update(worksheet="votes", data=df_votes[df_votes["書籍タイトル"] != t])
                st.rerun()
