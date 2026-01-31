import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 初期設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

st.markdown("""
    <style>
    [data-testid="column"] { padding: 0px 5px !important; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -10px !important; }
    .stButton button { border-radius: 4px; width: 100%; height: 32px !important; padding: 0px !important; font-size: 14px !important; }
    div[data-testid="stTextInput"] > div > div > input { height: 32px !important; font-size: 14px !important; }
    hr { margin: 5px 0 !important; border: 0.1px solid #f0f2f6; }
    .main .block-container { padding-top: 1.5rem; max-width: 1000px; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# タブの状態を保持するセッション
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df_books = conn.read(worksheet="booklist", ttl=120)
        df_books.columns = df_books.columns.str.strip()
        df_votes = conn.read(worksheet="votes", ttl=0)
        if df_votes.empty:
            df_votes = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        df_votes.columns = df_votes.columns.str.strip()
        return df_books, df_votes
    except:
        return pd.DataFrame(), pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])

def save_votes(df):
    try:
        with st.spinner("スプレッドシートを更新中..."):
            conn.update(worksheet="votes", data=df)
            st.cache_data.clear()
            time.sleep(1.5)
            st.rerun()
    except:
        st.cache_data.clear()
        st.rerun()

df_books, df_votes = load_data()

# タブの作成（セッションから初期値を取得）
# ユーザーがタブを切り替えたら session_state を更新する仕組み
tabs = ["📖 Bookリスト", "🗳️ 投票・集計"]
# URLパラメータやsession_stateを使ってタブを固定
selected_tab = st.radio("ナビゲーション", tabs, index=st.session_state.active_tab, horizontal=True, label_visibility="collapsed")

# 選択されたタブをセッションに保存（リロード対策）
st.session_state.active_tab = tabs.index(selected_tab)

# --- 【1】Bookリスト画面 ---
if selected_tab == "📖 Bookリスト":
    st.header("候補に登録")
    if not df_books.empty:
        all_cats = ["すべて"] + list(df_books["カテゴリ"].unique())
        selected_cat = st.selectbox("カテゴリ表示", all_cats)
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.markdown(f"### 📂 {cat_name}")
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            
            h_c1, h_c2, h_c3, h_c4 = st.columns([3.5, 0.8, 1.5, 0.7])
            h_c1.caption("書籍名 / 著者")
            h_c2.caption("詳細")
            h_c3.caption("名前")
            h_c4.caption("登録")
            st.markdown("---")

            for _, row in cat_books.iterrows():
                title = row.get("書籍名", "無題")
                author = row.get("著者名", "不明")
                url = row.get("URL")
                
                c1, c2, c3, c4 = st.columns([3.5, 0.8, 1.5, 0.7])
                with c1:
                    st.markdown(f"**{title}** \n<small>{author}</small>", unsafe_allow_html=True)
                with c2:
                    if pd.notnull(url) and str(url).startswith("http"):
                        st.link_button("🔗", str(url))
                    else: st.write("")
                with c3:
                    name_input = st.text_input("名前", key=f"ni_{title}", label_visibility="collapsed", placeholder="名前")
                with c4:
                    if st.button("選ぶ", key=f"eb_{title}"):
                        if name_input:
                            new_row = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": name_input, "ポイント": 0}])
                            save_votes(pd.concat([df_votes, new_row], ignore_index=True))
                        else: st.toast("名前を入力！")
                st.markdown("<hr>", unsafe_allow_html=True)

# --- 【2】投票・集計画面 ---
if selected_tab == "🗳️ 投票・集計":
    st.subheader("👤 ユーザー設定")
    my_name = st.text_input("あなたの名前を入力してください", key="my_login_name")

    admin_col1, admin_col2 = st.columns(2)
    with admin_col1:
        if st.button("全得点リセット"):
            save_votes(df_votes[df_votes["アクション"] == "選出"])
    with admin_col2:
        if st.button("全データ消去", type="primary"):
            save_votes(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))

    st.divider()

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
        my_v_data = df_votes[(df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票")]
        voted_1_book = my_v_data[my_v_data["ポイント"].astype(float) == 1]["書籍タイトル"].tolist()
        voted_2_book = my_v_data[my_v_data["ポイント"].astype(float) == 2]["書籍タイトル"].tolist()
        has_voted_1 = len(voted_1_book) > 0
        has_voted_2 = len(voted_2_book) > 0

        if st.button(f"🚩 {my_name}さんの投票をすべて取り消す"):
            filtered_df = df_votes[~((df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票"))]
            save_votes(filtered_df)

        st.subheader("🗳️ 投票エリア")
        nominated = df_votes[df_votes["アクション"] == "選出"]
        
        if nominated.empty:
            st.info("選出された候補がまだありません。")
        else:
            for _, n_row in nominated.iterrows():
                b_title = n_row["書籍タイトル"]
                this_p = 0
                if b_title in voted_1_book: this_p = 1
                if b_title in voted_2_book: this_p = 2
                
                vc1, vc2, vc3 = st.columns([3, 0.6, 0.6])
                vc1.markdown(f"**{b_title}** <small>({n_row['ユーザー名']}さん選出)</small>", unsafe_allow_html=True)
                
                d1 = has_voted_1 or (this_p == 2)
                if vc2.button(f"+1", key=f"p1_{b_title}", type="primary" if this_p==1 else "secondary", disabled=d1):
                    new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 1}])
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))

                d2 = has_voted_2 or (this_p == 1)
                if vc3.button(f"+2", key=f"p2_{b_title}", type="primary" if this_p==2 else "secondary", disabled=d2):
                    new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 2}])
                    save_votes(pd.concat([df_votes, new_v], ignore_index=True))
                st.markdown("---")
