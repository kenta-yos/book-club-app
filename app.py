import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import time

# --- Supabase 接続 ---
# secrets.toml に SUPABASE_URL と SUPABASE_KEY を設定してください
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- ページ設定 ---
st.set_page_config(page_title="Book Club", layout="wide")

# CSSは以前のものを継承
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .main .block-container { padding-top: 2rem; max-width: 900px; }
    .book-row { padding: 15px 0; border-bottom: 1px solid #ececec; width: 100%; margin-bottom: 5px; }
    .title-text { font-weight: 600; color: #1a1a1a; margin-bottom: 4px; line-height: 1.5; }
    .author-text { color: #707070; font-size: 0.85rem; line-height: 1.2; }
    .stButton button { border-radius: 6px; height: 36px !important; }
    </style>
    """, unsafe_allow_html=True)

# セッション管理
if "page" not in st.session_state: st.session_state.page = "list"
if "user_name" not in st.session_state: st.session_state.user_name = ""

def fetch_data():
    try:
        # Books取得
        res_b = supabase.table("books").select("*").execute()
        df_b = pd.DataFrame(res_b.data)
        
        # Votes取得（booksテーブルのtitleもJOIN）
        res_v = supabase.table("votes").select("*, books(title)").execute()
        raw_v = res_v.data
        
        processed_v = []
        for v in raw_v:
            row = v.copy()
            # book_idに紐づくタイトルを「書籍タイトル」として展開
            row["書籍タイトル"] = v["books"]["title"] if v.get("books") else "削除された本"
            processed_v.append(row)
        
        df_v = pd.DataFrame(processed_v)
        if df_v.empty:
            df_v = pd.DataFrame(columns=["id", "created_at", "action", "book_id", "user_name", "points", "書籍タイトル"])
            
        return df_b, df_v
    except Exception as e:
        st.error(f"データ連携エラー: {e}")
        return pd.DataFrame(), pd.DataFrame()

def save_and_refresh(table, data, message="完了"):
    with st.spinner("更新中..."):
        try:
            supabase.table(table).insert(data).execute()
            st.cache_data.clear()
            msg = st.success(message)
            time.sleep(1)
            msg.empty()
            st.rerun()
        except Exception as e:
            st.error(f"保存エラー: {e}")

# データのロード
df_books, df_votes = fetch_data()

# --- TOP: NAME ENTRY ---
st.title("読書会アプリ (Supabase UUID版)")
u_name = st.text_input("お名前を入力してください", value=st.session_state.user_name, placeholder="Your Name")
st.session_state.user_name = u_name.strip()

if not st.session_state.user_name:
    st.info("💡 アプリを利用するには名前を入力してください。")
    st.stop()

# --- NAVIGATION ---
c_nav1, c_nav2, c_nav3 = st.columns([1, 1, 3])
with c_nav1:
    if st.button("📖 本を選ぶ", use_container_width=True, type="primary" if st.session_state.page == "list" else "secondary"):
        st.session_state.page = "list"
        st.rerun()
with c_nav2:
    if st.button("🗳️ 投票する", use_container_width=True, type="primary" if st.session_state.page == "vote" else "secondary"):
        st.session_state.page = "vote"
        st.rerun()
with c_nav3:
    if st.button("🔄 最新の状態に更新"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- PAGE 1: BOOK LIST ---
if st.session_state.page == "list":
    st.header("Book List")
    
    # 選出チェック (UUIDは文字列として扱う)
    my_selection = df_votes[(df_votes["user_name"] == st.session_state.user_name) & (df_votes["action"] == "選出")]
    nominated_ids = df_votes[df_votes["action"] == "選出"]["book_id"].unique().tolist()

    if not my_selection.empty:
        st.success("✅ あなたはすでに本を1冊選出しています。")
        if st.button("選出をキャンセルして選び直す"):
            target_book_id = str(my_selection.iloc[0]["book_id"])
            supabase.table("votes").delete().eq("book_id", target_book_id).execute()
            st.cache_data.clear()
            st.rerun()

    if df_books.empty:
        st.info("書籍データが登録されていません。")
    else:
        for cat in df_books["category"].dropna().unique():
            st.subheader(f"📂 {cat}")
            cat_books = df_books[df_books["category"] == cat]
            for _, row in cat_books.iterrows():
                b_id = str(row["id"])
                is_nominated = b_id in nominated_ids
                
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    st.markdown(f"<div class='title-text'>{row['title']}</div><div class='author-text'>{row['author']}</div>", unsafe_allow_html=True)
                with c2:
                    if row["url"]: st.link_button("詳細", row["url"], use_container_width=True)
                with c3:
                    # 自分が選出済み or すでに誰かが選出済みなら無効
                    btn_disabled = is_nominated or not my_selection.empty
                    btn_label = "選出済" if is_nominated else "選ぶ"
                    if st.button(btn_label, key=f"sel_{b_id}", disabled=btn_disabled, use_container_width=True):
                        save_and_refresh("votes", {
                            "action": "選出",
                            "book_id": b_id,
                            "user_name": st.session_state.user_name
                        })
                st.markdown('<div class="book-row"></div>', unsafe_allow_html=True)

# --- PAGE 2: VOTE ---
else:
    # 投票画面も同様にUUID(b_id)ベースで処理
    st.header("🏆 Ranking")
    nominated_rows = df_votes[df_votes["action"] == "選出"]
    
    if nominated_rows.empty:
        st.info("まだ候補が選ばれていません。")
    else:
        vote_only = df_votes[df_votes["action"] == "投票"]
        summary = []
        for _, n in nominated_rows.iterrows():
            b_id = n["book_id"]
            b_votes = vote_only[vote_only["book_id"] == b_id]
            summary.append({
                "タイトル": n["書籍タイトル"],
                "点数": b_votes["points"].sum(),
                "内訳": ", ".join([f"{v['user_name']}({v['points']})" for _, v in b_votes.iterrows()]) or "-"
            })
        st.table(pd.DataFrame(summary).sort_values("点数", ascending=False))

        st.divider()
        st.subheader(f"🗳️ {st.session_state.user_name} さんの投票")
        
        my_votes = vote_only[vote_only["user_name"] == st.session_state.user_name]
        v_points = my_votes["points"].tolist()

        for _, n in nominated_rows.iterrows():
            b_id = n["book_id"]
            current_p = my_votes[my_votes["book_id"] == b_id]["points"].sum()
            
            vc1, vc2, vc3 = st.columns([3, 1, 1])
            with vc1:
                st.write(f"**{n['書籍タイトル']}**")
            
            with vc2:
                # 1点の持ち票があるか、またはこの本に既に投票済みの場合はdisabled
                d1 = (1 in v_points) or (current_p > 0)
                if st.button("+1点", key=f"v1_{b_id}", disabled=d1, use_container_width=True):
                    save_and_refresh("votes", {"action": "投票", "book_id": b_id, "user_name": st.session_state.user_name, "points": 1})
            with vc3:
                # 2点の持ち票があるか、またはこの本に既に投票済みの場合はdisabled
                d2 = (2 in v_points) or (current_p > 0)
                if st.button("+2点", key=f"v2_{b_id}", disabled=d2, use_container_width=True):
                    save_and_refresh("votes", {"action": "投票", "book_id": b_id, "user_name": st.session_state.user_name, "points": 2})
