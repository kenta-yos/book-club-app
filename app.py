import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 初期設定 ---
st.set_page_config(page_title="読書会選書アプリ", layout="wide")
st.title("📚 読書会 選書＆投票アプリ")

# シークレットから情報を取得
try:
    SPREADSHEET_URL = st.secrets["gsheets"]["public_url"]
    GEMINI_API_KEY = st.secrets["gemini"]["api_key"]
except KeyError:
    st.error("Secretsの設定が見つかりません。")
    st.stop()

# Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Google Sheetsへの接続
conn = st.connection("gsheets", type=GSheetsConnection)

# --- データ読み込み ---
def load_data():
    # スプレッドシートのIDを抽出して、CSV形式で直接読み込む（最もエラーが少ない方法）
    sheet_id = "1SnZqt_VqsmHJAePrdUdrtmXnfzaGj4VBlYDZ1F3T8yc"
    
    # booklistシートの読み込み
    url_books = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=booklist"
    df_books = pd.read_csv(url_books)
    
    # votesシートの読み込み
    try:
        url_votes = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=votes"
        df_votes = pd.read_csv(url_votes)
    except Exception:
        df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        
    return df_books, df_votes

df_books, df_votes = load_data()

# セッション状態（一時保存用）の初期化
if "local_votes" not in st.session_state:
    st.session_state.local_votes = df_votes

# --- サイドバーナビゲーション ---
menu = st.sidebar.radio("メニュー", ["Bookリスト", "投票画面"])

# --- AIチャット機能 (サイドバー) ---
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI選書コンシェルジュ")
user_input = st.sidebar.text_input("どんな本が読みたい？", placeholder="例：社会学で読みやすい本は？")

if user_input:
    # 読み込んだリストに基づいて回答
    book_context = df_books[['書籍名', '著者名', 'カテゴリ']].to_string()
    prompt = f"以下のリスト内の本のみを使って、ユーザーの要望に答えてください。\n\n【リスト】\n{book_context}\n\n【要望】\n{user_input}"
    with st.sidebar.status("AIが考えています..."):
        response = model.generate_content(prompt)
    st.sidebar.info(response.text)

# --- メインコンテンツ ---

if menu == "Bookリスト":
    st.header("📖 書籍一覧")
    
    # カテゴリで絞り込み
    if "カテゴリ" in df_books.columns:
        categories = ["すべて"] + list(df_books["カテゴリ"].unique())
        selected_cat = st.selectbox("カテゴリで絞り込み", categories)
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]
    else:
        display_df = df_books

    # カテゴリごとに表示
    for cat in display_df["カテゴリ"].unique():
        with st.expander(f"📂 {cat}", expanded=True):
            cat_books = display_df[display_df["カテゴリ"] == cat]
            for _, row in cat_books.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"**{row['書籍名']}** ({row['著者名']})")
                if col2.button("詳細・選ぶ", key=f"sel_{row['書籍名']}"):
                    st.session_state.temp_book = row

    # 詳細表示
    if "temp_book" in st.session_state:
        book = st.session_state.temp_book
        st.markdown("---")
        st.subheader(f"📌 {book['書籍名']}")
        st.write(f"著者: {book['著者名']}")
        if "URL" in book and pd.notnull(book['URL']):
            st.link_button("詳細サイト（外部URL）へ", book['URL'])
        
        u_name = st.text_input("あなたの名前を入力してください")
        if st.button("この本を候補に選ぶ"):
            if u_name:
                new_data = {"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "選出", "書籍タイトル": book['書籍名'], "ユーザー名": u_name, "ポイント": 0}
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([new_data])], ignore_index=True)
                st.success(f"{u_name}さんが「{book['書籍名']}」を候補に入れました！")
                del st.session_state.temp_book
                st.rerun()
            else:
                st.error("名前を入力してください")

else: # 投票画面
    st.header("🗳️ 投票・集計")
    v_df = st.session_state.local_votes
    
    # 「選出」された本を特定
    nominated = v_df[v_df["アクション"] == "選出"]["書籍タイトル"].unique()
    
    if len(nominated) == 0:
        st.info("まだ候補の本が選ばれていません。Bookリストから「この本を選出する」を押してください。")
    else:
        # スコア計算
        scores = v_df.groupby("書籍タイトル")["ポイント"].sum().reset_index()
        st.subheader("現在のランキング")
        st.table(scores.sort_values("ポイント", ascending=False))
        
        st.markdown("---")
        for title in nominated:
            # その本を最初に選んだ人を取得
            n_rows = v_df[(v_df["書籍タイトル"] == title) & (v_df["アクション"] == "選出")]
            n_name = n_rows.iloc[0]['ユーザー名'] if not n_rows.empty else "不明"
            
            st.write(f"### {title}")
            st.caption(f"候補に追加した人: {n_name} さん")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            if c1.button("+2", key=f"p2_{title}"):
                new_v = {"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "投票", "書籍タイトル": title, "ユーザー名": "", "ポイント": 2}
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([new_v])], ignore_index=True)
                st.rerun()
            if c2.button("+1", key=f"p1_{title}"):
                new_v = {"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "投票", "書籍タイトル": title, "ユーザー名": "", "ポイント": 1}
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([new_v])], ignore_index=True)
                st.rerun()
            if c3.button("-1", key=f"m1_{title}"):
                new_v = {"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "投票", "書籍タイトル": title, "ユーザー名": "", "ポイント": -1}
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([new_v])], ignore_index=True)
                st.rerun()
            if c4.button("-2", key=f"m2_{title}"):
                new_v = {"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "投票", "書籍タイトル": title, "ユーザー名": "", "ポイント": -2}
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([new_v])], ignore_index=True)
                st.rerun()
            if c5.button("選出取消", key=f"del_{title}", type="primary"):
                st.session_state.local_votes = v_df[v_df["書籍タイトル"] != title]
                st.rerun()
