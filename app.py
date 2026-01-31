import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

# CSSで全体の見た目を調整
st.markdown("""
    <style>
    /* ボタンの共通スタイル */
    .stButton button { width: 100%; border-radius: 5px; }
    /* サイドバーを完全に非表示にする */
    [data-testid="stSidebar"] { display: none; }
    /* メインコンテンツの幅と余白の調整 */
    .main .block-container { padding-top: 1.5rem; max-width: 900px; }
    /* 水平線の余白を調整 */
    hr { margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

# 1. スプレッドシート接続設定
# Secretsから接続情報を取得し、秘密鍵の改行コードを補正する
creds_dict = dict(st.secrets["connections"]["gsheets"])
if "private_key" in creds_dict:
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

conn = st.connection("gsheets", type=GSheetsConnection, **creds_dict)

# 2. データ読み込み関数
def load_data():
    # 書籍リスト（マスターデータ）
    df_books = conn.read(worksheet="booklist", ttl=0)
    df_books.columns = df_books.columns.str.strip()
    
    # 投票データ
    try:
        df_votes = conn.read(worksheet="votes", ttl=0)
        df_votes.columns = df_votes.columns.str.strip()
    except:
        # シートが空または存在しない場合の初期化
        df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
    
    return df_books, df_votes

df_books, df_votes = load_data()

# 3. 書き込み（更新）用関数
def save_votes(df):
    conn.update(worksheet="votes", data=df)
    st.cache_data.clear() # キャッシュをクリアして最新を反映
    st.rerun()

# 自分の投票状況をブラウザのセッション内で保持
if "my_votes" not in st.session_state:
    st.session_state.my_votes = {} # {書籍タイトル: 投票ポイント}

# --- メイン画面レイアウト ---
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- 【1】Bookリスト画面 ---
with tab_list:
    st.header("読みたい本を候補に登録")
    
    # カテゴリフィルタ
    all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
    selected_cat = st.selectbox("カテゴリ表示切替", all_cats)
    
    display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

    # カテゴリごとにグルーピング表示
    for cat_name in display_df["カテゴリ"].unique():
        st.subheader(f"📂 {cat_name}")
        cat_books = display_df[display_df["カテゴリ"] == cat_name]
        
        for _, row in cat_books.iterrows():
            title = row.get("書籍名", "無題")
            author = row.get("著者名", "不明")
            url = row.get("URL", "#")

            with st.expander(f"📔 {title} / {author}"):
                if pd.notnull(url) and str(url).startswith("http"):
                    st.link_button("🔗 書籍詳細を表示", str(url))
                
                # 選出フォーム
                with st.form(key=f"form_{title}"):
                    u_name = st.text_input("あなたの名前", key=f"name_{title}")
                    if st.form_submit_button("この本を読書会候補に選ぶ"):
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
                            st.warning("名前を入力してください")

# --- 【2】投票・集計画面 ---
with tab_vote:
    # --- 管理者リセットボタンを右上に配置 ---
    header_col, reset_col1, reset_col2 = st.columns([4, 1.5, 1.5])
    
    with header_col:
        st.header("みんなの投票状況")
    
    with reset_col1:
        st.write("") # レイアウト微調整用の余白
        if st.button("得点リセット", help="選出された本は残し、得点（+1/+2）だけを全消去します"):
            reset_df = df_votes[df_votes["アクション"] == "選出"]
            st.session_state.my_votes = {}
            save_votes(reset_df)
            
    with reset_col2:
        st.write("") 
        if st.button("全データ消去", type="primary", help="選出された本も含め、すべてのデータをリセットします"):
            st.session_state.my_votes = {}
            save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))

    st.divider()
    
    # 1. 現在のランキング表示
    if not df_votes.empty:
        summary = df_votes.groupby("書籍タイトル")["ポイント"].sum().reset_index()
        summary = summary.sort_values("ポイント", ascending=False)
        st.subheader("🏆 現在のランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)
    
    st.divider()
    
    # 2. 投票アクションエリア
    nominated = df_votes[df_votes["アクション"] == "選出"]
    
    if nominated.empty:
        st.info("現在、選出された本はありません。Bookリストから選んでください。")
    else:
        st.subheader("🗳️ 投票する")
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            n_user = n_row["ユーザー名"]
            
            # 自分がこの本に投票したポイントを確認
            current_my_point = st.session_state.my_votes.get(b_title, 0)
            
            with st.container():
                st.markdown(f"**{b_title}** (選出: {n_user}さん)")
                v_col1, v_col2, v_col3 = st.columns([1, 1, 1])
                
                # ポイントボタンのタイプ（選択中は primary = 色付き）
                type_p1 = "primary" if current_my_point == 1 else "secondary"
                type_p2 = "primary" if current_my_point == 2 else "secondary"

                if v_col1.button(f"＋1", key=f"v1_{b_title}", type=type_p1):
                    new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 1}])
                    st.session_state.my_votes[b_title] = 1
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))

                if v_col2.button(f"＋2", key=f"v2_{b_title}", type=type_p2):
                    new_v = pd.DataFrame([{"日時": datetime.now(), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 2}])
                    st.session_state.my_votes[b_title] = 2
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))

                if v_col3.button("取消", key=f"rm_{b_title}"):
                    # その本に対する「投票」データを削除
                    removed_df = df_votes[~((df_votes["書籍タイトル"] == b_title) & (df_votes["アクション"] == "投票"))]
                    st.session_state.my_votes[b_title] = 0
                    save_votes(removed_df)
                st.divider()
