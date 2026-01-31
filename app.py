import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- ページ設定 ---
st.set_page_config(page_title="Book Club", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .main .block-container { padding-top: 2rem; max-width: 900px; }
    [data-testid="column"] { display: flex; flex-direction: column; justify-content: center; padding: 10px 10px !important; }
    .book-row { padding: 15px 0; border-bottom: 1px solid #ececec; width: 100%; margin-bottom: 5px; }
    .title-text { font-weight: 600; color: #1a1a1a; margin-bottom: 4px; line-height: 1.5; }
    .author-text { color: #707070; font-size: 0.85rem; line-height: 1.2; }
    .stButton button { border-radius: 6px; height: 36px !important; border: 1px solid #e0e0e0; }
    div[data-testid="stTextInput"] input { border-radius: 6px !important; height: 40px !important; }
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
        df_v = df_v if not df_v.empty else pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"])
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

# --- NAVIGATION ---
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
        cats = ["すべて"] + list(df_books["カテゴリ"].unique())
        selected_cat = st.selectbox("カテゴリを絞り込む", cats, label_visibility="collapsed")
        display_df = df_books if selected_cat == "すべて" else df_books[df_books["カテゴリ"] == selected_cat]

        for cat_name in display_df["カテゴリ"].unique():
            st.markdown(f"<div style='margin: 25px 0 10px 0; color:#333; font-weight:bold;'>📂 {cat_name}</div>", unsafe_allow_html=True)
            cat_books = display_df[display_df["カテゴリ"] == cat_name]
            for _, row in cat_books.iterrows():
                title, author, url = row.get("書籍名", "無題"), row.get("著者名", "不明"), row.get("URL")
                c1, c2, c3 = st.columns([4, 0.8, 0.8])
                with c1:
                    st.markdown(f"<div class='title-text'>{title}</div><div class='author-text'>{author}</div>", unsafe_allow_html=True)
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
    st.subheader("🏆 Ranking")
    if not df_votes.empty:
        # ポイントを数値化
        df_v = df_votes.copy()
        df_v["ポイント"] = pd.to_numeric(df_v["ポイント"], errors='coerce').fillna(0)
        
        # 投票データのみ抽出
        vote_data = df_v[df_v["アクション"] == "投票"]
        
        # 書籍ごとの合計点と内訳を作成
        summary_list = []
        # 全ての選出された書籍をベースにする
        all_nominated = df_v[df_v["アクション"] == "選出"]["書籍タイトル"].unique()
        
        for title in all_nominated:
            # その本への投票を抽出
            b_votes = vote_data[vote_data["書籍タイトル"] == title]
            total_p = b_votes["ポイント"].sum()
            
            # 内訳文字列を作成 例: "山田(2), 田中(1)"
            details = ", ".join([f"{r['ユーザー名']}({int(r['ポイント'])})" for _, r in b_votes.iterrows()])
            
            summary_list.append({
                "書籍タイトル": title,
                "合計点": total_p,
                "投票者内訳": details if details else "-"
            })
            
        summary_df = pd.DataFrame(summary_list).sort_values("合計点", ascending=False)
        st.dataframe(summary_df, hide_index=True, use_container_width=True)
    
    st.divider()
    
    my_name = st.session_state.user_name
    st.subheader(f"🗳️ {my_name} さんの投票")
    
    my_v_data = df_votes[(df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票")]
    voted_titles = {row["書籍タイトル"]: row["ポイント"] for _, row in my_v_data.iterrows()}

    if st.button("自分の投票をすべて取消", key="revoke"):
        save_and_refresh(df_votes[~((df_votes["ユーザー名"] == my_name) & (df_votes["アクション"] == "投票"))])

    st.write("")
    nominated_rows = df_votes[df_votes["アクション"] == "選出"]
    
    if nominated_rows.empty:
        st.info("候補がまだ選ばれていません。")
    else:
        for _, n_row in nominated_rows.iterrows():
            b_title = n_row["書籍タイトル"]
            this_p = voted_titles.get(b_title, 0)
            
            vc1, vc2, vc3 = st.columns([3, 0.7, 0.7])
            with vc1:
                st.markdown(f"<div class='title-text'>{b_title}</div><div class='author-text'>推薦：{n_row['ユーザー名']}さん</div>", unsafe_allow_html=True)
            
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

    with st.expander("Admin Settings"):
        if st.button("全得点リセット"):
            save_and_refresh(df_votes[df_votes["アクション"] == "選出"])
        if st.button("全データ完全消去", type="primary"):
            save_and_refresh(pd.DataFrame(columns=["日時", "アクション", "書籍タイトル", "ユーザー名", "ポイント"]))
