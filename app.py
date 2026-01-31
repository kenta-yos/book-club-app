import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 初期設定 ---
st.set_page_config(page_title="読書会選書アプリ", layout="wide")
st.title("📚 読書会 選書＆投票アプリ")

# シークレットから情報を取得
SPREADSHEET_URL = st.secrets["gsheets"]["public_url"]
GEMINI_API_KEY = st.secrets["gemini"]["api_key"]

# Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Google Sheetsへの接続
conn = st.connection("gsheets", type=GSheetsConnection)

# --- データ読み込み ---
def load_data():
    # 本のリストを読み込み
    df_books = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Bookリスト_アプリ用")
    # 投票結果を読み込み
    try:
        df_votes = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="投票結果")
    except:
        df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
    return df_books, df_votes

df_books, df_votes = load_data()

# --- サイドバーナビゲーション ---
menu = st.sidebar.radio("メニュー", ["Bookリスト", "投票画面"])

# --- AIチャット機能 (サイドバー) ---
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI選書コンシェルジュ")
user_input = st.sidebar.text_input("どんな本が読みたい？", placeholder="例：社会学で読みやすい本は？")

if user_input:
    # リストの情報をテキスト化してAIに渡す
    book_context = df_books[['書籍名', '著者名', 'カテゴリ']].to_string()
    prompt = f"""
    あなたは読書会のコンシェルジュです。以下のリストにある本の中から、ユーザーの要望に合うものを提案してください。
    リストにない本は絶対に提案しないでください。本の内容や背景を詳しく解説してください。
    
    【書籍リスト】
    {book_context}
    
    【ユーザーの要望】
    {user_input}
    """
    response = model.generate_content(prompt)
    st.sidebar.info(response.text)

# --- メインコンテンツ ---

if menu == "Bookリスト":
    st.header("📖 書籍一覧")
    
    # カテゴリで絞り込み
    categories = ["すべて"] + list(df_books["カテゴリ"].unique())
    selected_cat = st.selectbox("カテゴリで絞り込み", categories)
    
    display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]
    
    # カテゴリごとに表示
    for cat in display_df["カテゴリ"].unique():
        with st.expander(f"📂 {cat}", expanded=True):
            cat_books = display_df[display_df["カテゴリ"] == cat]
            for _, row in cat_books.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{row['書籍名']}** ({row['著者名']})")
                with col2:
                    if st.button("詳細・選ぶ", key=f"btn_{row['書籍名']}"):
                        st.session_state.selected_book = row
                        st.rerun()

    # 詳細モーダル風表示
    if "selected_book" in st.session_state:
        book = st.session_state.selected_book
        st.markdown("---")
        st.subheader(f"📌 {book['書籍名']}")
        st.write(f"著者: {book['著者名']}")
        st.link_button("詳細サイトへ（外部URL）", book['URL'])
        
        user_name = st.text_input("あなたの名前を入力してください")
        if st.button("この本を選出する"):
            if user_name:
                new_row = pd.DataFrame([{
                    "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "アクション": "選出",
                    "書籍タイトル": book['書籍名'],
                    "ユーザー名": user_name,
                    "ポイント": 0
                }])
                # 更新処理（簡易的に表示のみ。実際はconn.updateが必要だが公開設定による）
                st.success(f"{user_name}さんが「{book['書籍名']}」を選出しました！シートに書き込んでください。")
                # 💡 本来はここでconn.updateを行うが、権限設定が複雑なため、
                # 運用上は「スプレッドシートに手動で追記」か、API経由で書き込む設定が必要
                st.info("※投票結果シートに「選出」アクションを記録しました（シミュレーション）")
                # 便宜上、session_stateで管理
                if "local_votes" not in st.session_state: st.session_state.local_votes = df_votes
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, new_row])
                del st.session_state.selected_book
                st.rerun()
            else:
                st.error("名前を入力してください")

elif menu == "投票画面":
    st.header("🗳️ 投票・集計")
    
    # 選出された本のみを抽出
    if "
