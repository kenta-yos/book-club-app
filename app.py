import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

st.markdown("""
    <style>
    .stButton button { border-radius: 5px; }
    [data-testid="stSidebar"] { display: none; }
    .main .block-container { padding-top: 1.5rem; max-width: 900px; }
    hr { margin: 0.8rem 0; }
    </style>
    """, unsafe_allow_html=True)

# 1. スプレッドシート接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. データ読み込み関数
def load_data():
    try:
        df_books = conn.read(worksheet="booklist", ttl=1)
        df_books.columns = df_books.columns.str.strip()
        
        df_votes = conn.read(worksheet="votes", ttl=1)
        if df_votes.empty:
            return df_books, pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント", "UID"])
        
        df_votes.columns = df_votes.columns.str.strip()
        return df_books, df_votes
    except:
        return pd.DataFrame(), pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント", "UID"])

df_books, df_votes = load_data()

# 3. 書き込み用関数
def save_votes(df):
    try:
        cols = ["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント", "UID"]
        if df.empty:
            df = pd.DataFrame(columns=cols)
        else:
            for c in cols:
                if c not in df.columns: df[c] = None
            df = df[cols]
            
        conn.update(worksheet="votes", data=df)
        st.cache_data.clear()
        time.sleep(1.5) 
        st.rerun()
    except Exception as e:
        st.error("保存に失敗しました。再操作してください。")

# ユーザー識別用
if "user_id" not in st.session_state:
    st.session_state.user_id = datetime.now().strftime("%Y%m%d%H%M%S")

# 現在の自分の投票済み状況を確認（セッションをまたいでもデータから判定）
# UIDとアクションが「投票」のデータを抽出
my_current_votes = df_votes[(df_votes["UID"].astype(str) == st.session_state.user_id) & (df_votes["アクション"] == "投票")]
# すでに＋1、＋2をそれぞれ使ったかどうかのフラグ
has_voted_1 = 1 in my_current_votes["ポイント"].astype(float).values
has_voted_2 = 2 in my_current_votes["ポイント"].astype(float).values

# --- メイン画面 ---
tab_list, tab_vote = st.tabs(["📖 Bookリスト", "🗳️ 投票・集計"])

# --- 【1】Bookリスト画面 ---
with tab_list:
    st.header("候補に登録")
    if not df_books.empty:
        all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
        selected_cat = st.selectbox("カテゴリ表示", all_cats)
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.subheader(f"📂 {cat_name}")
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            for _, row in cat_books.iterrows():
                title = row.get("書籍名", "無題")
                with st.expander(f"📔 {title}"):
                    with st.form(key=f"form_{title}"):
                        u_name = st.text_input("名前", key=f"name_{title}")
                        if st.form_submit_button("選出"):
                            if u_name:
                                new_row = pd.DataFrame([{
                                    "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "アクション": "選出", "書籍タイトル": title, "ユーザー名": u_name, "ポイント": 0, "UID": st.session_state.user_id
                                }])
                                save_votes(pd.concat([df_votes, new_row], ignore_index=True))

# --- 【2】投票・集計画面 ---
with tab_vote:
    h_col, a_col = st.columns([2, 3])
    with h_col: st.header("投票状況")
    
    with a_col:
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("自分の投票をクリア"):
                df_temp = df_votes.copy()
                df_temp["UID"] = df_temp["UID"].astype(str).str.strip()
                target_uid = str(st.session_state.user_id).strip()
                
                # 自分の「投票」アクション行のみを除外して保存
                filtered_df = df_temp[~((df_temp["アクション"] == "投票") & (df_temp["UID"] == target_uid))]
                save_votes(filtered_df)
        with c2:
            if st.button("得点リセット"):
                save_votes(df_votes[df_votes["アクション"] == "選出"])
        with c3:
            if st.button("全リセット", type="primary"):
                save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント", "UID"]))

    st.divider()
    
    # ランキング表示（自分の投票をクリアした後はここから数値が消える）
    if not df_votes.empty:
        df_summary = df_votes.copy()
        df_summary["ポイント"] = pd.to_numeric(df_summary["ポイント"], errors='coerce').fillna(0)
        summary = df_summary.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.subheader("🏆 ランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)
    
    st.divider()
    
    nominated = df_votes[df_votes["アクション"] == "選出"]
    if nominated.empty:
        st.info("候補がありません。")
    else:
        st.subheader("🗳️ 投票（+1, +2 各1回まで）")
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            
            # この本に自分が何点入れているか確認
            this_book_my_vote = my_current_votes[my_current_votes["書籍タイトル"] == b_title]
            my_voted_p = this_book_my_vote["ポイント"].astype(float).sum() if not this_book_my_vote.empty else 0
            
            r_col1, r_col2, r_col3 = st.columns([3, 0.6, 0.6])
            r_col1.markdown(f"**{b_title}** <small>({n_row['ユーザー名']}さん選出)</small>", unsafe_allow_html=True)
            
            # ＋1ボタンの活性/非活性判定
            # 1. すでにどこかの本で+1を使っている OR 2. この本ですでに+2を使っている
            disable_1 = has_voted_1 or (my_voted_p == 2)
            if r_col2.button(f"+1", key=f"v1_{b_title}", type="primary" if my_voted_p==1 else "secondary", disabled=disable_1):
                new_v = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 1, "UID": st.session_state.user_id}])
                save_votes(pd.concat([df_votes, new_v], ignore_index=True))
            
            # ＋2ボタンの活性/非活性判定
            # 1. すでにどこかの本で+2を使っている OR 2. この本ですでに+1を使っている
            disable_2 = has_voted_2 or (my_voted_p == 1)
            if r_col3.button(f"+2", key=f"v2_{b_title}", type="primary" if my_voted_p==2 else "secondary", disabled=disable_2):
                new_v = pd.DataFrame([{"日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": "匿名", "ポイント": 2, "UID": st.session_state.user_id}])
                save_votes(pd.concat([df_votes, new_v], ignore_index=True))
            st.markdown("---")
