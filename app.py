import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="読書会アプリ", layout="wide")

# 1. 接続設定
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"初期設定エラー: {e}")
    st.stop()

# 2. データの読み込み
def load_data():
    try:
        # booklistシートの読み込み
        df_b = conn.read(worksheet="booklist", ttl=5)
        # votesシートの読み込み（失敗した場合は空のシートを作成）
        try:
            df_v = conn.read(worksheet="votes", ttl=0)
        except:
            df_v = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        
        # 列名の空白削除
        df_b.columns = df_b.columns.str.strip()
        df_v.columns = df_v.columns.str.strip()
        return df_b, df_v
    except Exception as e:
        st.error(f"読み込み失敗。SecretsのURLやAPI設定を確認してください: {e}")
        st.stop()

df_books, df_votes = load_data()

# 3. 画面表示
tab1, tab2 = st.tabs(["📖 本の一覧", "🗳️ 投票と集計"])

with st.sidebar:
    st.subheader("🤖 AI相談")
    q = st.text_input("本選びの相談はこちら")
    if q:
        res = model.generate_content(f"以下のリストからおすすめを教えて：\n{df_books.to_string()}\n質問：{q}")
        st.info(res.text)

with tab1:
    for _, r in df_books.iterrows():
        title = r['書籍名']
        with st.expander(f"📔 {title} / {r['著者名']}"):
            if pd.notnull(r.get('URL')): st.link_button("詳細を見る", str(r['URL']))
            with st.form(f"form_{title}"):
                u_name = st.text_input("お名前", key=f"user_{title}")
                if st.form_submit_button("候補に選ぶ"):
                    if u_name:
                        new_data = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": u_name, "ポイント": 0}])
                        conn.update(worksheet="votes", data=pd.concat([df_votes, new_data]))
                        st.success("追加しました！")
                        st.rerun()

with tab2:
    if df_votes.empty:
        st.info("まだ候補の本がありません。")
    else:
        # 集計表示
        st.subheader("現在のランキング")
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.table(summary)
        
        st.divider()
        # 投票ボタン
        titles = df_votes[df_votes["アクション"] == "選出"]["書籍タイトル"].unique()
        for t in titles:
            st.write(f"### {t}")
            c1, c2, c3 = st.columns(3)
            def add_vote(p):
                v = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d"), "アクション": "投票", "書籍タイトル": t, "ユーザー名": "匿名", "ポイント": p}])
                conn.update(worksheet="votes", data=pd.concat([df_votes, v]))
                st.rerun()
            if c1.button("+1点", key=f"up_{t}"): add_vote(1)
            if c2.button("-1点", key=f"down_{t}"): add_vote(-1)
            if c3.button("候補から外す", key=f"del_{t}"):
                conn.update(worksheet="votes", data=df_votes[df_votes["書籍タイトル"] != t])
                st.rerun()
