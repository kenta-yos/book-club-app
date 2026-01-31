import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- ページ基本設定 ---
st.set_page_config(page_title="読書会アプリ", layout="wide")

st.markdown("""
    <style>
    [data-testid="column"] { padding: 0px 5px !important; }
    .stButton button { border-radius: 4px; width: 100%; height: 36px !important; }
    hr { margin: 8px 0 !important; border: 0.1px solid #f0f2f6; }
    .main .block-container { padding-top: 1.5rem; max-width: 1000px; }
    div[data-testid="stTextInput"] > div > div > input { height: 36px !important; }
    </style>
    """, unsafe_allow_html=True)

# セッション状態の初期化
if "page" not in st.session_state: st.session_state.page = "list"
if "user_name" not in st.session_state: st.session_state.user_name = ""

conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data():
    try:
        df_b = conn.read(worksheet="booklist", ttl=300)
        df_v = conn.read(worksheet="votes", ttl=0)
        df_b.columns = df_b.columns.str.strip()
        if df_v.empty:
            df_v = pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
        df_v.columns = df_v.columns.str.strip()
        return df_b, df_v
    except:
        return pd.DataFrame(), pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])

def save_and_refresh(df):
    try:
        conn.update(worksheet="votes", data=df)
        st.cache_data.clear()
        time.sleep(1.2)
        st.rerun()
    except:
        st.cache_data.clear()
        st.rerun()

df_books, df_votes = fetch_data()

# --- 【最上部】名前入力エリア ---
# 名前が入力されたら session_state に保存
u_name = st.text_input("👤 あなたのお名前を入力してください（必須）", value=st.session_state.user_name, placeholder="例：山田 太郎")
st.session_state.user_name = u_name.strip()

if not st.session_state.user_name:
    st.warning("⚠️ アプリを利用するには、まずお名前を入力してください。")
    st.stop() # ここで処理を止めることで、名前がない間は下のUIを表示させない

# --- 【上部】ナビゲーション ---
c_nav1, c_nav2, c_nav3 = st.columns([1, 1, 3])
with c_nav1:
    if st.button("📖 Bookリスト", type="primary" if st.session_state.page == "list" else "secondary"):
        st.session_state.page = "list"
        st.rerun()
with c_nav2:
    if st.button("🗳️ 投票・集計", type="primary" if st.session_state.page == "vote" else "secondary"):
        st.session_state.page = "vote"
        st.rerun()
with c_nav3:
    if st.button("🔄 更新", key="sync"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- 【1】Bookリストページ ---
if st.session_state.page == "list":
    st.header("候補に登録")
    if not df_books.empty:
        selected_cat = st.selectbox("カテゴリ表示", ["すべて"] + list(df_books["カテゴリ"].unique()), label_visibility="collapsed")
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.markdown(f"### 📂 {cat_name}")
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            
            h_c1, h_c2, h_c3 = st.columns([4.5, 0.8, 0.7])
            h_c1.caption("書籍名 / 著者")
            h_c2.caption("詳細")
            h_c3.caption("登録")
            st.divider()

            for _, row in cat_books.iterrows():
                title, author, url = row.get("書籍名", "無題"), row.get("著者名", "不明"), row.get("URL")
                c1, c2, c3 = st.columns([4.5, 0.8, 0.7])
                with c1:
                    st.markdown(f"**{title}** \n<small>{author}</small>", unsafe_allow_html=True)
                with c2:
                    if pd.notnull(url) and str(url).startswith("http"):
                        st.link_button("🔗", str(url))
                    else: st.write("")
                with c3:
                    # 名前入力は不要になったので「選ぶ」ボタンのみ
                    if st.button("選ぶ", key=f"eb_{title}"):
                        new_row = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": st.session_state.user_name, "ポイント": 0}])
                        save_and_refresh(pd.concat([df_votes, new_row], ignore_index=True))
                st.markdown("<hr>", unsafe_allow_html=True)

# --- 【2】投票・集計ページ ---
else:
    # 管理操作（スッキリまとめる）
    c_admin1, c_admin2 = st.columns(2)
    with c_admin1:
        if st.button("全得点リセット"):
            save_and_refresh(df_votes[df_votes["アクション"] == "選出"])
    with c_admin2:
        if st.button("全データ消去", type="primary"):
            save_and_refresh(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))

    st.divider()

    # ランキング表示
    if not df_votes.empty:
        df_v = df_votes.copy()
        df_v["ポイント"] = pd.to_numeric(df_v["ポイント"], errors='coerce').fillna(0)
        summary = df_v.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.subheader("🏆 ランキング")
        st.dataframe(summary, hide_index=True, use_container_width=True)

    st.divider()

    # 投票エリア
    my_name = st.session_state.user_name
    my_v_data = df_votes[(df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票")]
    voted_1_book = my_v_data[my_v_data["ポイント"].astype(float) == 1]["書籍タイトル"].tolist()
    voted_2_book = my_v_data[my_v_data["ポイント"].astype(float) == 2]["書籍タイトル"].tolist()
    has_voted_1, has_voted_2 = len(voted_1_book) > 0, len(voted_2_book) > 0

    c_cancel, _ = st.columns([2, 3])
    with c_cancel:
        if st.button(f"🚩 {my_name}さんの投票を取り消す"):
            filtered_df = df_votes[~((df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票"))]
            save_and_refresh(filtered_df)

    st.subheader("🗳️ 投票エリア")
    nominated = df_votes[df_votes["アクション"] == "選出"]
    
    if nominated.empty:
        st.info("選出された候補がまだありません。")
    else:
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            this_p = 1 if b_title in voted_1_book else (2 if b_title in voted_2_book else 0)
            
            vc1, vc2, vc3 = st.columns([3, 0.6, 0.6])
            vc1.markdown(f"**{b_title}** <small>({n_row['ユーザー名']}さん選出)</small>", unsafe_allow_html=True)
            
            d1 = has_voted_1 or (this_p == 2)
            if vc2.button(f"+1", key=f"p1_{b_title}", type="primary" if this_p==1 else "secondary", disabled=d1):
                new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 1}])
                save_and_refresh(pd.concat([df_votes, new_v], ignore_index=True))

            d2 = has_voted_2 or (this_p == 1)
            if vc3.button(f"+2", key=f"p2_{b_title}", type="primary" if this_p==2 else "secondary", disabled=d2):
                new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 2}])
                save_and_refresh(pd.concat([df_votes, new_v], ignore_index=True))
            st.markdown("---")
