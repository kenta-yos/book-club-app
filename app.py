import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

# CSSで見た目の調整
st.markdown("""
    <style>
    .stButton button { width: 100%; }
    .stExpander { border: 1px solid #e6e9ef; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# 1. スプレッドシート接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. データ読み込み関数
def load_data():
    # 書籍リスト（閲覧用）
    df_books = conn.read(worksheet="booklist", ttl=0)
    df_books.columns = df_books.columns.str.strip()
    
    # 投票データ（共有用）
    try:
        df_votes = conn.read(worksheet="votes", ttl=0)
        df_votes.columns = df_votes.columns.str.strip()
    except:
        # 万が一シートが空の場合の初期化
        df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
    
    return df_books, df_votes

df_books, df_votes = load_data()

# 3. 書き込み用関数
def save_votes(df):
    conn.update(worksheet="votes", data=df)
    st.cache_data.clear()
    st.rerun()

# --- サイドバー：AIチャット ---
with st.sidebar:
    st.subheader("🤖 AIコンシェルジュ")
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        user_input = st.text_input("どんな本を探してる？")
        if user_input:
            context = df_books[['書籍名', '著者名', 'カテゴリ']].to_string()
            prompt = f"リスト内の本だけで回答して。短く簡潔に。\n\n【リスト】\n{context}\n\n【要望】\n{user_input}"
            response = model.generate_content(prompt)
            st.info(response.text)
    except:
        st.warning("Gemini APIキーを設定してください")

# --- メイン画面：タブ設定 ---
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- 【1】Bookリスト画面 ---
with tab_list:
    st.header("読みたい本を候補に入れよう")
    
    all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
    selected_cat = st.selectbox("カテゴリ絞り込み", all_cats)
    
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
                    st.link_button("🔗 詳細を見る", str(url))
                
                with st.form(key=f"form_{title}"):
                    u_name = st.text_input("あなたの名前", key=f"name_{title}")
                    if st.form_submit_button("この本を候補に登録"):
                        if u_name:
                            new_row = pd.DataFrame([{
                                "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "アクション": "選出",
                                "書籍タイトル": title,
                                "ユーザー名": u_name,
                                "ポイント": 0
                            }])
                            save_votes(pd.concat([df_votes, new_row], ignore_index=True))
                        else:
                            st.warning("名前を入れてね")

# --- 【2】投票・集計画面 ---
with tab_vote:
    st.header("みんなの投票状況")
    
    # スコア集計
    if not df_votes.empty:
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index()
        summary = summary.sort_values("ポイント", ascending=False)
        st.subheader("🏆 現在のランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)
    
    st.divider()
    
    # 候補本の一覧
    nominated = df_votes[df_votes["アクション"] == "選出"]
    
    if nominated.empty:
        st.info("まだ候補がありません。リストから選んでください。")
    else:
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            n_user = n_row["ユーザー名"]
            
            with st.container():
                col1, col2 = st.columns([3, 2])
                col1.markdown(f"**{b_title}** (選出: {n_user}さん)")
                
                v_col1, v_col2, v_col3 = col2.columns(3)
                if v_col1.button("＋1", key=f"v1_{b_title}"):
                    new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 1}])
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))
                if v_col2.button("＋2", key=f"v2_{b_title}"):
                    new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 2}])
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))
                if v_col3.button("取消", key=f"rm_{b_title}", type="primary"):
                    # 自分の投票だけ消す簡易実装（この本に関連する全ての「投票」を消す）
                    removed_df = df_votes[~((df_votes["書籍タイトル"] == b_title) & (df_votes["アクション"] == "投票"))]
                    save_votes(removed_df)

    # 管理者リセット機能
    st.sidebar.divider()
    with st.sidebar.expander("⚙️ 管理者用リセット"):
        if st.button("ポイントだけ全消去"):
            # アクションが「選出」のものだけ残す
            reset_df = df_votes[df_votes["アクション"] == "選出"]
            save_votes(reset_df)
        if st.button("すべてのデータを全消去"):
            save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))
