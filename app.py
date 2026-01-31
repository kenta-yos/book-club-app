import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="読書会アプリ", layout="wide")

# API接続設定
try:
    # connections.gsheetsの設定を自動読み込み
    conn = st.connection("gsheets", type=GSheetsConnection)
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

def load_data():
    try:
        # worksheet名だけで読み込み（URLはSecretsから自動取得）
        df_b = conn.read(worksheet="booklist", ttl=5)
        try:
            df_v = conn.read(worksheet="votes", ttl=0)
        except:
            df_v = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        df_b.columns = df_b.columns.str.strip()
        return df_b, df_v
    except Exception as e:
        st.error(f"データ読み込み失敗: {e}")
        st.stop()

df_books, df_votes = load_data()

t1, t2 = st.tabs(["📖 リスト", "🗳️ 投票"])

# AIコンシェルジュ
with st.sidebar:
    st.subheader("🤖 AI相談")
    q = st.text_input("どんな本がいい？")
    if q:
        ctx = df_books[['書籍名', '著者名']].to_string()
        res = model.generate_content(f"{ctx}\n質問:{q}")
        st.info(res.text)

# リスト表示
with t1:
    cats = ["すべて"] + list(df_books["カテゴリ"].unique())
    sel = st.selectbox("カテゴリ", cats)
    disp = df_books if sel == "すべて" else df_books[df_books["カテゴリ"] == sel]

    for _, r in disp.iterrows():
        title = r['書籍名']
        with st.expander(f"📔 {title}"):
            if pd.notnull(r.get('URL')): st.link_button("詳細", str(r['URL']))
            with st.form(f"f_{title}"):
                name = st.text_input("名前", key=f"n_{title}")
                if st.form_submit_button("候補に入れる"):
                    if name:
                        row = {"日時": datetime.now().strftime("%Y-%m-%d"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": name, "ポイント": 0}
                        new_v = pd.concat([df_votes, pd.DataFrame([row])], ignore_index=True)
                        conn.update(worksheet="votes", data=new_v)
                        st.rerun()

# 投票表示
with t2:
    if df_votes.empty or "選出" not in df_votes["アクション"].values:
        st.info("まだ候補がありません")
    else:
        st.subheader("ランキング")
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.table(summary)
        
        st.divider()
        titles = df_votes[df_votes["アクション"] == "選出"]["書籍タイトル"].unique()
        for t in titles:
            st.write(f"### {t}")
            c1, c2, c3, c4 = st.columns(4)
            
            def vote(p):
                v = {"日時": datetime.now().strftime("%Y-%m-%d"), "アクション": "投票", "書籍タイトル": t, "ユーザー名": "匿名", "ポイント": p}
                conn.update(worksheet="votes", data=pd.concat([df_votes, pd.DataFrame([v])], ignore_index=True))
                st.rerun()

            if c1.button("+2", key=f"p2_{t}"): vote(2)
            if c2.button("+1", key=f"p1_{t}"): vote(1)
            if c3.button("-1", key=f"m1_{t}"): vote(-1)
            if c4.button("取消", key=f"dl_{t}", type="
