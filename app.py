import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- ページ設定 ---
st.set_page_config(page_title="Book Club", layout="wide")

# CSS: 究極のシンプルさと使いやすさを追求
st.markdown("""
    <style>
    /* 全体：ノイズを削る */
    .main { background-color: #ffffff; }
    [data-testid="column"] { padding: 0px 8px !important; }
    
    /* フォント：清潔感のあるサンセリフ */
    html, body, [class*="css"] { font-family: 'Segoe UI', Roboto, sans-serif; }
    
    /* ボタン：フラットで角丸を抑えめに */
    .stButton button {
        border-radius: 6px;
        height: 34px !important;
        font-weight: 500;
        border: 1px solid #e0e0e0;
    }
    
    /* 1行の区切りを美しく */
    .book-row {
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    
    /* 入力欄：背景を白く、枠を細く */
    div[data-testid="stTextInput"] input {
        border: 1px solid #dcdcdc !important;
        border-radius: 6px !important;
        height: 34px !important;
    }
    
    /* 見出しとキャプション */
    h1, h2, h3 { color: #212121; margin-bottom: 0.5rem; }
    small { color: #666; }
    
    .main .block-container { padding-top: 2rem; max-width: 900px; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# セッション管理
if "page" not in st.session_state: st.session_state.page = "list"
if "user_name" not in st.session_state: st.session_state.user_name = ""

conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data():
    try:
        df_b = conn.read(worksheet="booklist", ttl=120)
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
        time.sleep(1)
        st.rerun()
    except:
        st.rerun()

df_books, df_votes = fetch_data()

# --- TOP: NAME ENTRY ---
st.title("読書会アプリ")
u_name = st.text_input("お名前を入力してください", value=st.session_state.user_name, placeholder="Your Name")
st.session_state.user_name = u_name.strip()

if not st.session_state.user_name:
    st.info("💡 アプリを利用するには名前を入力してください。")
    st.stop()

# --- NAVIGATION: TABS STYLE ---
st.write("")
c_nav1, c_nav2, c_nav3 = st.columns([1, 1, 3])
with c_nav1:
    if st.button("📖 候補を選ぶ", use_container_width=True, type="primary" if st.session_state.page == "list" else "secondary"):
        st.session_state.page = "list"
        st.rerun()
with c_nav2:
    if st.button("🗳️ 投票・集計", use_container_width=True, type="primary" if st.session_state.page == "vote" else "secondary"):
        st.session_state.page = "vote"
        st.rerun()
with c_nav3:
    if st.button("🔄 更新", key="sync"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- PAGE 1: BOOK LIST ---
if st.session_state.page == "list":
    st.header("Book List")
    if not df_books.empty:
        selected_cat = st.selectbox("カテゴリを絞り込む", ["すべて"] + list(df_books["カテゴリ"].unique()))
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.write("")
            st.subheader(f"📂 {cat_name}")
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            
            for _, row in cat_books.iterrows():
                title, author, url = row.get("書籍名", "無題"), row.get("著者名", "不明"), row.get("URL")
                
                # 行デザイン
                with st.container():
                    c1, c2, c3 = st.columns([4, 0.8, 0.8])
                    with c1:
                        st.markdown(f"**{title}**<br><small>{author}</small>", unsafe_allow_html=True)
                    with c2:
                        if pd.notnull(url) and str(url).startswith("http"):
                            st.link_button("詳細", str(url), use_container_width=True)
                    with c3:
                        if st.button("選ぶ", key=f"sel_{title}", use_container_width=True):
                            new_row = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "選出", "書籍タイトル": title, "ユーザー名": st.session_state.user_name, "ポイント": 0}])
                            save_and_refresh(pd.concat([df_votes, new_row], ignore_index=True))
                    st.markdown('<div class="book-row"></div>', unsafe_allow_html=True)

# --- PAGE 2: VOTE & RANKING ---
else:
    # 集計
    st.header("Ranking")
    if not df_votes.empty:
        df_v = df_votes.copy()
        df_v["ポイント"] = pd.to_numeric(df_v["ポイント"], errors='coerce').fillna(0)
        summary = df_v.groupby("書籍タイトル")["ポイント"].sum().reset_index().sort_values("ポイント", ascending=False)
        st.dataframe(summary, hide_index=True, use_container_width=True)
    
    st.divider()
    
    # 投票
    my_name = st.session_state.user_name
    st.subheader(f"🗳️ {my_name}さんの投票")
    
    my_v_data = df_votes[(df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票")]
    voted_titles = {row["書籍タイトル"]: row["ポイント"] for _, row in my_v_data.iterrows()}

    c_rev, _ = st.columns([1.5, 3])
    if c_rev.button("投票を全てリセット", key="revoke", use_container_width=True):
        save_and_refresh(df_votes[~((df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票"))])

    st.write("")
    nominated = df_votes[df_votes["アクション"] == "選出"]
    
    if nominated.empty:
        st.info("候補がまだ選ばれていません。")
    else:
        for _, n_row in nominated.iterrows():
            b_title = n_row["書籍タイトル"]
            this_p = voted_titles.get(b_title, 0)
            
            with st.container():
                vc1, vc2, vc3 = st.columns([3, 0.7, 0.7])
                with vc1:
                    st.markdown(f"**{b_title}**<br><small>推薦：{n_row['ユーザー名']}さん</small>", unsafe_allow_html=True)
                
                d1 = (1 in voted_titles.values()) or (this_p == 2)
                with vc2:
                    if st.button(f"+1", key=f"v1_{b_title}", type="primary" if this_p==1 else "secondary", disabled=d1, use_container_width=True):
                        new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 1}])
                        save_and_refresh(pd.concat([df_votes, new_v], ignore_index=True))
                
                d2 = (2 in voted_titles.values()) or (this_p == 1)
                with vc3:
                    if st.button(f"+2", key=f"v2_{b_title}", type="primary" if this_p==2 else "secondary", disabled=d2, use_container_width=True):
                        new_v = pd.DataFrame([{"日時": datetime.now().strftime("%m/%d %H:%M"), "アクション": "投票", "書籍タイトル": b_title, "ユーザー名": my_name, "ポイント": 2}])
                        save_and_refresh(pd.concat([df_votes, new_v], ignore_index=True))
                st.markdown('<div class="book-row"></div>', unsafe_allow_html=True)

    # システム管理
    st.write("")
    with st.expander("管理者設定"):
        if st.button("全得点のみリセット"):
            save_and_refresh(df_votes[df_votes["アクション"] == "選出"])
        if st.button("全データ（候補含む）を完全消去", type="primary"):
            save_and_refresh(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))
