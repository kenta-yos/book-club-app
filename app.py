import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

# カスタムCSSでメニューを使いやすく
st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 5px; }
    .book-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# データの保持（投票データをセッション間で維持）
if "local_votes" not in st.session_state:
    st.session_state.local_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])

# シークレット取得
try:
    SHEET_ID = "1SnZqt_VqsmHJAePrdUdrtmXnfzaGj4VBlYDZ1F3T8yc"
    GEMINI_API_KEY = st.secrets["gemini"]["api_key"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("設定エラー: Secretsを確認してください")
    st.stop()

# --- データ読み込み関数 ---
@st.cache_data(ttl=60) # 1分間キャッシュして高速化
def load_book_list():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=booklist"
    df = pd.read_csv(url, header=0)
    df.columns = df.columns.str.strip()
    return df

df_books = load_book_list()

# --- 上部ナビゲーション（タブ形式で固定） ---
# スマホでも押しやすいよう、サイドバーではなくメイン画面上部に配置
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- AIチャット（サイドバーに配置） ---
with st.sidebar:
    st.subheader("🤖 AIコンシェルジュ")
    user_input = st.text_input("どんな本を探してる？", placeholder="例：泣ける本を教えて")
    if user_input:
        context = df_books[['書籍名', '著者名', 'カテゴリ']].to_string()
        prompt = f"リスト内の本だけで回答して下さい。回答は短く簡潔に。\n\n【リスト】\n{context}\n\n【要望】\n{user_input}"
        response = model.generate_content(prompt)
        st.info(response.text)

# --- 【1】Bookリスト画面 ---
with tab_list:
    st.header("読みたい本を選ぼう")
    
    # カテゴリ絞り込み
    all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
    selected_cat = st.selectbox("カテゴリ表示切替", all_cats)
    
    display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

    for _, row in display_df.iterrows():
        title = row.get("書籍名", "無題")
        author = row.get("著者名", "不明")
        cat = row.get("カテゴリ", "-")
        url = row.get("URL", "#")

        # 各書籍を「開閉式（expander）」にして詳細を閉じ込める
        with st.expander(f"📔 {title} / {author}"):
            st.write(f"**カテゴリ:** {cat}")
            if pd.notnull(url) and str(url).startswith("http"):
                st.link_button("🔗 書籍詳細サイトを表示", str(url))
            
            # 選出フォーム
            with st.form(key=f"form_{title}"):
                u_name = st.text_input("あなたの名前", key=f"name_{title}")
                submit = st.form_submit_button("この本を読書会候補に選ぶ")
                if submit:
                    if u_name:
                        new_row = pd.DataFrame([{
                            "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "アクション": "選出",
                            "書籍タイトル": title,
                            "ユーザー名": u_name,
                            "ポイント": 0
                        }])
                        st.session_state.local_votes = pd.concat([st.session_state.local_votes, new_row], ignore_index=True)
                        st.success(f"{title} を候補に追加しました！「投票」タブを見てね。")
                    else:
                        st.warning("名前を入力してください")

# --- 【2】投票画面 ---
with tab_vote:
    st.header("みんなで投票")
    v_df = st.session_state.local_votes
    
    # 選出された本の一覧を取得
    nominated = v_df[v_df["アクション"] == "選出"]
    
    if nominated.empty:
        st.info("まだ本が選ばれていません。Bookリストから選んでください。")
    else:
        # スコア集計
        score_summary = v_df.groupby("書籍タイトル")["ポイント"].sum().reset_index()
        score_summary = score_summary.sort_values("ポイント", ascending=False)
        
        st.subheader("現在の集計結果")
        st.dataframe(score_summary, hide_index=True, use_container_width=True)
        
        st.divider()
        
        # 候補ごとの投票ボタン
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            n_user = n_row["ユーザー名"]
            
            # 各候補をカード風に表示
            st.markdown(f"### {b_title}")
            st.caption(f"選んだ人: {n_user}さん")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            if col1.button("＋2", key=f"p2_{b_title}"):
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([{"書籍タイトル": b_title, "ポイント": 2, "アクション": "投票"}])], ignore_index=True)
                st.rerun()
            if col2.button("＋1", key=f"p1_{b_title}"):
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([{"書籍タイトル": b_title, "ポイント": 1, "アクション": "投票"}])], ignore_index=True)
                st.rerun()
            if col3.button("ー1", key=f"m1_{b_title}"):
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([{"書籍タイトル": b_title, "ポイント": -1, "アクション": "投票"}])], ignore_index=True)
                st.rerun()
            if col4.button("ー2", key=f"m2_{b_title}"):
                st.session_state.local_votes = pd.concat([st.session_state.local_votes, pd.DataFrame([{"書籍タイトル": b_title, "ポイント": -2, "アクション": "投票"}])], ignore_index=True)
                st.rerun()
            if col5.button("取消", key=f"del_{b_title}", type="primary"):
                st.session_state.local_votes = st.session_state.local_votes[st.session_state.local_votes["書籍タイトル"] != b_title]
                st.rerun()
            st.divider()
