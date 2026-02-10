import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import time

# --- Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- ページ設定 ---
st.set_page_config(page_title="Book Club", layout="wide")

# スタイル調整
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] { justify-content: center !important; }
    .stButton button { border-radius: 8px; }
    /* ログインボタンを大きく見せる */
    .login-btn button { height: 100px !important; font-size: 1.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# セッション管理
if "page" not in st.session_state: st.session_state.page = "list"
if "USER" not in st.session_state: st.session_state.USER = None
if "U_ICON" not in st.session_state: st.session_state.U_ICON = "👤"

# --- データ取得 ---
def fetch_users():
    res = supabase.table("users").select("user_name, icon").execute()
    return pd.DataFrame(res.data)

def fetch_data():
    res_b = supabase.table("books").select("*").execute()
    df_b = pd.DataFrame(res_b.data)
    
    # votes と books を JOIN して取得
    res_v = supabase.table("votes").select("*, books(title)").execute()
    processed_v = []
    for v in res_v.data:
        row = v.copy()
        row["書籍タイトル"] = v["books"]["title"] if v.get("books") else "削除された本"
        processed_v.append(row)
    df_v = pd.DataFrame(processed_v)
    
    if df_v.empty:
        df_v = pd.DataFrame(columns=["id", "created_at", "action", "book_id", "user_name", "points", "書籍タイトル"])
    return df_b, df_v

def save_and_refresh(table, data, message="完了"):
    with st.spinner("更新中..."):
        try:
            # 常に現在のログインユーザー名を付与して保存
            data["user_name"] = st.session_state.USER
            supabase.table(table).insert(data).execute()
            st.cache_data.clear()
            msg = st.success(message)
            time.sleep(1)
            msg.empty()
            st.rerun()
        except Exception as e:
            st.error(f"保存エラー: {e}")

# --- 1. ログイン処理 ---
user_df = fetch_users()

if not st.session_state.USER:
    st.markdown("<h2 style='text-align: center; margin-top: 2rem;'>📚 Book Club Login</h2>", unsafe_allow_html=True)
    
    if not user_df.empty:
        user_list = user_df.sort_values("user_name").to_dict('records')
        # 3人ずつ分割して表示
        for i in range(0, len(user_list), 3):
            # 💡 horizontal=True を指定することでスマホでも横並びを維持します
            with st.container(horizontal=True):
                chunk = user_list[i:i+3]
                for row in chunk:
                    btn_key = f"l_{row['user_name']}"
                    
                    # ボタン内の改行とアイコン表示。use_container_widthで幅を揃えます
                    if st.button(f"{row['icon']}\n{row['user_name']}", key=btn_key, use_container_width=True):
                        # ログ出力（テーブル名は適宜合わせてください）
                        try:
                            supabase.table("access_logs").insert({"user_name": row['user_name']}).execute()
                        except:
                            pass # ログ用テーブルがない場合はスキップ
                            
                        st.session_state.USER = row['user_name']
                        st.session_state.U_ICON = row['icon']
                        st.query_params["user"] = row['user_name']
                        st.rerun()
        st.stop()

# --- 2. メインコンテンツ ---
df_books, df_votes = fetch_data()

# ヘッダー
c_head1, c_head2 = st.columns([0.8, 0.2])
with c_head1:
    st.subheader(f"{st.session_state.U_ICON} {st.session_state.USER} さんとしてログイン中")
with c_head2:
    if st.button("ログアウト", use_container_width=True):
        st.session_state.USER = None
        st.rerun()

# ナビゲーション
nav_cols = st.columns([1, 1, 3])
with nav_cols[0]:
    if st.button("📖 本を選ぶ", use_container_width=True, type="primary" if st.session_state.page == "list" else "secondary"):
        st.session_state.page = "list"
        st.rerun()
with nav_cols[1]:
    if st.button("🗳️ 投票する", use_container_width=True, type="primary" if st.session_state.page == "vote" else "secondary"):
        st.session_state.page = "vote"
        st.rerun()

st.divider()

# --- PAGE 1: BOOK LIST ---
if st.session_state.page == "list":
    st.header("Book List")
    
    # 自分がすでに選出しているかチェック
    my_selection = df_votes[(df_votes["user_name"] == st.session_state.USER) & (df_votes["action"] == "選出")]
    nominated_ids = df_votes[df_votes["action"] == "選出"]["book_id"].unique().tolist()

    if not my_selection.empty:
        st.success("✅ 1冊選出済みです。")
        if st.button("選出をキャンセルして選び直す"):
            target_id = str(my_selection.iloc[0]["book_id"])
            supabase.table("votes").delete().eq("book_id", target_id).execute()
            st.rerun()

    for cat in df_books["category"].dropna().unique():
        st.subheader(f"📂 {cat}")
        for _, row in df_books[df_books["category"] == cat].iterrows():
            b_id = str(row["id"])
            is_nominated = b_id in nominated_ids
            
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(f"**{row['title']}** \n<small>{row['author']}</small>", unsafe_allow_html=True)
            with c2:
                if row["url"]: st.link_button("詳細", row["url"], use_container_width=True)
            with c3:
                disabled = is_nominated or not my_selection.empty
                label = "選出済" if is_nominated else "選ぶ"
                if st.button(label, key=f"sel_{b_id}", disabled=disabled, use_container_width=True):
                    save_and_refresh("votes", {"action": "選出", "book_id": b_id})

# --- PAGE 2: VOTE ---
else:
    st.header("🏆 Ranking")
    nominated_rows = df_votes[df_votes["action"] == "選出"]
    
    if nominated_rows.empty:
        st.info("まだ候補が選ばれていません。")
    else:
        vote_only = df_votes[df_votes["action"] == "投票"]
        summary = []
        
        # ユーザーテーブルからアイコンを取得するための辞書作成
        user_icon_map = dict(zip(user_df['user_name'], user_df['icon']))
        
        for _, n in nominated_rows.iterrows():
            b_id = n["book_id"]
            b_votes = vote_only[vote_only["book_id"] == b_id]
            
            # 投票内訳：アイコンと名前を表示
            details = ", ".join([
                f"{user_icon_map.get(v['user_name'], '👤')}{v['user_name']}({int(v['points'])})" 
                for _, v in b_votes.iterrows()
            ])
            
            summary.append({
                "タイトル": n["書籍タイトル"],
                "合計点": int(b_votes["points"].sum()), # 小数点削除
                "投票内訳": details if details else "-"
            })
        
        # DataFrame作成
        ranking_df = pd.DataFrame(summary)
        
        if not ranking_df.empty:
            # 合計点で降順ソート
            ranking_df = ranking_df.sort_values("合計点", ascending=False)
            # インデックス（左端の番号）を非表示にして表示
            st.dataframe(ranking_df, hide_index=True, use_container_width=True)
            
        st.divider()
        
        st.subheader("🗳️ 投票")
        
        my_votes = vote_only[vote_only["user_name"] == st.session_state.USER]
        v_points = my_votes["points"].tolist()

        for _, n in nominated_rows.iterrows():
            b_id = n["book_id"]
            current_p = my_votes[my_votes["book_id"] == b_id]["points"].sum()
            
            vc1, vc2, vc3 = st.columns([3, 1, 1])
            with vc1:
                st.write(f"**{n['書籍タイトル']}**")
            with vc2:
                d1 = (1 in v_points) or (current_p > 0)
                if st.button("+1点", key=f"v1_{b_id}", disabled=d1, use_container_width=True):
                    save_and_refresh("votes", {"action": "投票", "book_id": b_id, "points": 1})
            with vc3:
                d2 = (2 in v_points) or (current_p > 0)
                if st.button("+2点", key=f"v2_{b_id}", disabled=d2, use_container_width=True):
                    save_and_refresh("votes", {"action": "投票", "book_id": b_id, "points": 2})
