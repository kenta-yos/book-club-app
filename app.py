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
# ttlを300秒（5分）に設定し、通常時のAPI負荷を下げます
def load_data():
    try:
        df_books = conn.read(worksheet="booklist", ttl=300)
        df_books.columns = df_books.columns.str.strip()
        
        # 投票データは更新頻度が高いのでttlを短く（または書き込み時にクリア）
        df_votes = conn.read(worksheet="votes", ttl=300)
        if df_votes.empty:
            df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        df_votes.columns = df_votes.columns.str.strip()
        return df_books, df_votes
    except Exception as e:
        st.error("データの取得に失敗しました。少し待ってからブラウザを更新してください。")
        return pd.DataFrame(), pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])

# 3. 書き込み用関数
def save_votes(df):
    try:
        with st.spinner("スプレッドシートを更新中..."):
            conn.update(worksheet="votes", data=df)
            # 💡 ここが重要：保存に成功したら、キャッシュをクリアして最新を強制取得させる
            st.cache_data.clear()
            time.sleep(2) # Google側の反映ラグを待つ
            st.rerun()
    except Exception as e:
        st.error("Google Sheetsの制限により保存できませんでした。1分ほど置いてからやり直してください。")

# データの取得
df_books, df_votes = load_data()

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
                        u_name = st.text_input("あなたの名前（必須）", key=f"n_{title}")
                        if st.form_submit_button("候補に選ぶ"):
                            if u_name:
                                new_row = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": u_name, "ポイント": 0}])
                                save_votes(pd.concat([df_votes, new_row], ignore_index=True))
                            else:
                                st.error("名前を入力してください")

# --- 【2】投票・集計画面 ---
with tab_vote:
    st.subheader("👤 ユーザー設定")
    my_name = st.text_input("あなたの名前を入力してください", key="my_login_name", help="投票やクリアを行うために必要です")

    # 管理ボタンは横並びでスッキリ
    admin_col1, admin_col2 = st.columns(2)
    with admin_col1:
        if st.button("全得点リセット"):
            save_votes(df_votes[df_votes["アクション"] == "選出"])
    with admin_col2:
        if st.button("全データ消去", type="primary"):
            save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))

    st.divider()

    # ランキング表示
    if not df_votes.empty:
        df_v = df_votes.copy()
        df_v["ポイント"] = pd.to_numeric(df_v["ポイント"], errors='coerce').fillna(0)
        summary = df_v.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.subheader("🏆 ランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)

    st.divider()

    if not my_name:
        st.info("名前を入力すると投票機能が有効になります。")
    else:
        # 現在の自分の投票状況をスキャン
        my_v_data = df_votes[(df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票")]
        voted_1_book = my_v_data[my_v_data["ポイント"].astype(float) == 1]["書籍タイトル"].tolist()
        voted_2_book = my_v_data[my_v_data["ポイント"].astype(float) == 2]["書籍タイトル"].tolist()
        
        has_voted_1 = len(voted_1_book) > 0
        has_voted_2 = len(voted_2_book) > 0

        if st.button(f"🚩 {my_name}さんの投票をすべて取り消す"):
            filtered_df = df_votes[~((df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票"))]
            save_votes(filtered_df)

        st.subheader("🗳️ 投票（+1, +2 各1回まで）")
        nominated = df_votes[df_votes["アクション"] == "選出"]
        
        if nominated.empty:
            st.info("選出された候補がまだありません。")
        else:
            for _, n_row in nominated.iterrows():
                b_title = n_row["書籍タイトル"]
                this_p = 0
                if b_title in voted_1_book: this_p = 1
                if b_title in voted_2_book: this_p = 2
                
                c1, c2, c3 = st.columns([3, 0.6, 0.6])
                c1.markdown(f"**{b_title}** <small>({n_row['ユーザー名']}さん選出)</small>", unsafe_allow_html=True)
                
                # 制御ロジック
                d1 = has_voted_1 or (this_p == 2)
                if c2.button(f"+1", key=f"p1_{b_title}", type="primary" if this_p==1 else "secondary", disabled=d1):
                    new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 1}])
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))

                d2 = has_voted_2 or (this_p == 1)
                if c3.button(f"+2", key=f"p2_{b_title}", type="primary" if this_p==2 else "secondary", disabled=d2):
                    new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 2}])
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))
                st.markdown("---")
