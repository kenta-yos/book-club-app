import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import time
import plotly.express as px

# --- Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- ページ設定 ---
st.set_page_config(page_title="Book Club", layout="wide")

# スタイル調整
st.markdown("""
    <style>    
    /* ① ヘッダー（上部のバーとメニューボタン）を消す */
    header {visibility: hidden;}
    
    /* ② フッター（Made with Streamlit）を消す */
    footer {visibility: hidden;}
    
    /* ③ 上部の余白を詰める（消したヘッダー分の隙間を埋める） */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }

    /* 既存のスタイル */
    [data-testid="stHorizontalBlock"] { justify-content: center !important; }
    .stButton button { border-radius: 8px; }

    /* タイトルリンク設定 */
    .book-title-link {
        text-decoration: none !important;
        transition: opacity 0.2s;
    }

    /* 表形式を維持したまま中身を折り返す設定 */
    .history-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    .history-table th, .history-table td {
        border-bottom: 1px solid #eee;
        padding: 10px 5px;
        text-align: left;
    }
    .history-table th {
        color: #888;
        font-weight: normal;
        font-size: 0.8rem;
    }
    /* 内訳セル専用：チップを並べて折り返す */
    .tags-cell {
        display: flex;
        flex-wrap: wrap; /* これで表の中でも折り返す */
        gap: 4px;
    }
    
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

def fetch_categories():
    # categoriesテーブルから名前を取得。なければ固定リストを返します
    try:
        res = supabase.table("categories").select("name").order("id").execute()
        return [item["name"] for item in res.data]
    except:
        return ["カテゴリエラー"] # 失敗時のバックアップ

def fetch_data():
    res_b = supabase.table("books").select("*").execute()
    df_b = pd.DataFrame(res_b.data)
    
    res_v = supabase.table("votes").select("*").execute()
    df_v_raw = pd.DataFrame(res_v.data)
    
    if df_v_raw.empty:
        df_v = pd.DataFrame(columns=["id", "created_at", "action", "book_id", "user_name", "points", "書籍タイトル", "著者名"])
    else:
        df_b_subset = df_b[["id", "title", "author"]].rename(
            columns={"id": "book_id", "title": "書籍タイトル", "author": "著者名"}
        )
        df_v_raw["book_id"] = df_v_raw["book_id"].astype(str)
        df_b_subset["book_id"] = df_b_subset["book_id"].astype(str)
        
        df_v = pd.merge(df_v_raw, df_b_subset, on="book_id", how="left")
        
    return df_b, df_v
    
def fetch_events():
    try:
        res = supabase.table("events").select("*, books(*)").order("event_date", desc=True).execute()
        if not res.data:
            return pd.DataFrame(columns=["event_date", "book_id", "books"])
            
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"イベントデータ取得エラー: {e}")
        return pd.DataFrame(columns=["event_date", "book_id", "books"])

def save_and_refresh(table, data, message=""):
    try:
        # ログインユーザー名を付与
        data["user_name"] = st.session_state.USER
        supabase.table(table).insert(data).execute()
        st.cache_data.clear()
        # 画面右下にふわっと出る通知
        st.toast(message, icon="🚀")
        # 待ち時間を消して即リロード
        st.rerun()
    except Exception as e:
        st.error(f"エラーが発生しちゃった😢: {e}")
        
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

# --- メインコンテンツ部分 ---
df_books, df_votes = fetch_data()
df_events = fetch_events()

# --- データの加工 ---
# 1. すべてのイベント（過去・未来問わず）に登録された本のIDを取得
used_book_ids = [str(x) for x in df_events["book_id"].unique().tolist()] if not df_events.empty else []

# 2. Books一覧から、イベントで使用済みの本を除外する
df_display_books = df_books[~df_books["id"].astype(str).isin(used_book_ids)]

# 3. 選出・投票データからも、既に使用された本のデータを除外する
# これにより、Booksタブの「選出済」判定や、Votesタブのランキングから「確定済の本」が消えます。
# かつ、選んだ人の「1冊選出済み」フラグもリセットされます。
df_active_votes = df_votes[~df_votes["book_id"].astype(str).isin(used_book_ids)]

# 固定ヘッダー（ログインユーザー表示）
c_head1, c_head_upd = st.columns([0.8, 0.2])
with c_head1:
    st.subheader(f"{st.session_state.U_ICON} {st.session_state.USER} さん")
with c_head_upd:
    if st.button("🔄 更新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ② 次回の読書会（TOPインフォメーション）
# カラムが存在するかチェックしてから処理
if "event_date" in df_events.columns and not df_events.empty:
    today = datetime.now().strftime("%Y-%m-%d")
    future_events = df_events[df_events["event_date"] >= today]
    
    if not future_events.empty:
        # 未来のイベントがある場合
        next_ev = future_events.sort_values("event_date").iloc[0]
        b_info = next_ev.get("books") if next_ev.get("books") else {}
        b_url = b_info.get("url")
        
        with st.container(border=True):
            st.markdown(f"📅 **次回の開催: {next_ev['event_date']}**")
            
            # ✨ ここを修正：URLがあればリンクにし、なければテキストのみ表示
            if b_url and str(b_url).startswith("http"):
                st.markdown(f"📖 **課題本: [{b_info.get('title', '未定')}]({b_url})**")
            else:
                st.markdown(f"📖 **課題本: {b_info.get('title', '未定')}**")
                
    else:
        # 未来のイベントがない場合
        with st.container(border=True):
            st.info("📅 次回の開催は未定です。")
else:
    # テーブルが完全に空、またはエラーの場合
    with st.container(border=True):
        st.info("📅 次回の開催は未定です。")

# --- タブの作成 ---
tab1, tab2, tab3, tab4 = st.tabs(["📖 Books", "🗳️ Votes", "📜 History", "⚙️ Admin"])

# --- PAGE 1: BOOK LIST ---
with tab1:
    # --- 🆕 本の登録フォーム ---
    with st.expander("➕ 新しい本を登録する"):
        cat_list = fetch_categories() # マスタから取得
        with st.form("add_book_form", clear_on_submit=True):
            new_title = st.text_input("* 書籍タイトル")
            new_author = st.text_input("著者名")
            new_cat = st.radio("カテゴリーを選択", cat_list, horizontal=True)
            new_url = st.text_input("詳細URL（出版社URLなど）")
            submit_book = st.form_submit_button("本を登録する", use_container_width=True, type="primary")
            
            if submit_book:
                if new_title:
                    book_data = {
                        "title": new_title,
                        "author": new_author,
                        "category": new_cat,
                        "url": new_url,
                        "created_by": st.session_state.USER  # ログインユーザーを記録
                    }
                    try:
                        supabase.table("books").insert(book_data).execute()
                        st.cache_data.clear()
                        st.toast(f"「{new_title}」を登録しました", icon="🚀")
                        st.rerun() # 即座に反映
                    except Exception as e:
                        st.error(f"登録エラー: {e}")
                else:
                    st.warning("タイトルは必ず入力してね🙏")
    
    # --- 2. カテゴリ絞り込みリスト ---
    unique_cats = sorted(df_display_books["category"].dropna().unique().tolist())
    filter_options = ["すべて"] + unique_cats
    
    selected_cat = st.pills("カテゴリで絞り込み", filter_options, default="すべて")

    # 3. フィルタリング（ここが重要！）
    if selected_cat == "すべて":
        df_filtered = df_display_books
    else:
        # 選んだカテゴリと完全に一致するものだけに絞る
        df_filtered = df_display_books[df_display_books["category"] == selected_cat]
        
    # --- 3. 選出状況チェック ---
    my_selection = df_active_votes[(df_active_votes["user_name"] == st.session_state.USER) & (df_active_votes["action"] == "選出")]
    nominated_ids = df_active_votes[df_active_votes["action"] == "選出"]["book_id"].unique().tolist()

    if not my_selection.empty:
        st.success("✅ 1冊選出済みです")
        if st.button("選出をキャンセルして選び直す", use_container_width=True):
            target_id = str(my_selection.iloc[0]["book_id"])
            supabase.table("votes").delete().eq("book_id", target_id).eq("user_name", st.session_state.USER).eq("action", "選出").execute()
            st.cache_data.clear()
            st.toast("選出をキャンセルしたよ", icon="🙋")
            st.rerun()

    # --- 5. 本の表示（df_filtered を使用） ---
    if df_filtered.empty:
        st.info("該当する本がありません。")
    else:
        # 💡 df_filtered からカテゴリを抽出
        categories = df_filtered["category"].dropna().unique()
        
        for cat in categories:
            st.markdown(f"### 📂 {cat}")
            # 💡 ループ内も df_filtered を参照するように変更
            category_books = df_filtered[df_filtered["category"] == cat]
            
            for _, row in category_books.iterrows():
                b_id = str(row["id"])
                is_nominated = b_id in nominated_ids
                b_url = row["url"] if pd.notnull(row["url"]) and str(row["url"]).startswith("http") else None
                
                with st.container(border=True):
                    # --- A. タイトル・著者エリア ---
                    if b_url:
                        # リンクがある場合は青色（#1E88E5）
                        st.markdown(f"""
                            <div style="margin-bottom: 12px;">
                                <a href="{b_url}" target="_blank" class="book-title-link">
                                    <div style="font-size: 1.15rem; font-weight: bold; color: #1E88E5; line-height: 1.4;">
                                        {row['title']}
                                    </div>
                                </a>
                                <div style="color: #888; font-size: 0.8rem; margin-top: 4px;">{row['author']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # リンクがない場合は通常の黒色
                        st.markdown(f"""
                            <div style="margin-bottom: 12px;">
                                <div style="font-size: 1.15rem; font-weight: bold; color: #333; line-height: 1.4;">
                                    {row['title']}
                                </div>
                                <div style="color: #888; font-size: 0.8rem; margin-top: 4px;">{row['author']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    # --- B. 選出ボタンエリア ---
                    # 詳細ボタンを消したので、ボタン1つを大きく配置
                    if not my_selection.empty and b_id == str(my_selection.iloc[0]["book_id"]):
                        st.button("✅ これを選んだ", disabled=True, use_container_width=True, key=f"my_{b_id}")
                    elif is_nominated:
                        st.button("選出済", disabled=True, use_container_width=True, key=f"nom_{b_id}")
                    else:
                        is_disabled = not my_selection.empty
                        btn_label = "これを選ぶ" if not is_disabled else "既に選出済みです"
                        if st.button(btn_label, key=f"sel_{b_id}", disabled=is_disabled, use_container_width=True, type="primary"):
                            save_and_refresh("votes", {"action": "選出", "book_id": b_id}, f"「{row['title']}」を選出したよ👍")
                            
# --- 7. PAGE 2: RANKING & VOTE ---
with tab2:
    st.header("🏆 Ranking")
    nominated_rows = df_active_votes[df_active_votes["action"] == "選出"]

    if nominated_rows.empty:
        st.info("まだ候補が選ばれていません。")
    else:
        vote_only = df_active_votes[df_active_votes["action"] == "投票"]
        user_icon_map = dict(zip(user_df['user_name'], user_df['icon']))
        url_map = dict(zip(df_books['id'].astype(str), df_books['url']))
        
        # 最高得点の計算
        max_p = 0
        all_stats = []
        for _, n in nominated_rows.iterrows():
            p = int(vote_only[vote_only["book_id"] == str(n["book_id"])]["points"].sum())
            if p > max_p: max_p = p
            all_stats.append(p)

        # --- 1. ランキング表示（超コンパクト） ---
        ranking_html = ""
        for i, (_, n) in enumerate(nominated_rows.iterrows()):
            pts = all_stats[i]
            is_top = (pts == max_p and max_p > 0)
            
            b_votes = vote_only[vote_only["book_id"] == str(n["book_id"])]
            details = " ".join([f"{user_icon_map.get(v['user_name'], '👤') if is_top else ''}{int(v['points'])}" for _, v in b_votes.iterrows()])
            
            prefix = "👑 " if is_top else ""
            pts_color = "#FBC02D" if is_top else "#1E88E5"
            
            ranking_html += f"""
            <div style="margin-bottom: 4px; line-height: 1.2;">
                {prefix}<b>{n['書籍タイトル']}</b> 
                <span style="font-size: 1.15rem; font-weight: bold; color: {pts_color}; margin-left: 6px;">{pts}</span>
                <span style="font-size: 0.7rem; color: #888;">pts</span>
                <span style="font-size: 0.8rem; color: #999; margin-left: 8px;">{details}</span>
            </div>
            <hr style="margin: 4px 0; border: 0; border-top: 1px solid #eee;">
            """
        st.markdown(ranking_html, unsafe_allow_html=True)

        # --- 2. 投票セクション（パネルUI復活版） ---
        st.divider()
        st.subheader("🗳️ 投票")
        my_votes = vote_only[vote_only["user_name"] == st.session_state.USER]
        v_points = my_votes["points"].tolist()
        
        for _, n in nominated_rows.iterrows():
            b_id = str(n["book_id"])
            current_p = int(my_votes[my_votes["book_id"] == b_id]["points"].sum())
            b_url = url_map.get(b_id)
            n_user = n["user_name"]
            n_icon = user_icon_map.get(n_user, "👤")
            is_my_nomination = (n_user == st.session_state.USER)
            
            with st.container(border=True):
                # タイトルリンク（青色・下線なし）
                if pd.notnull(b_url) and str(b_url).startswith("http"):
                    title_style = "color: #1E88E5; text-decoration: none; font-weight: bold; font-size: 1.05rem;"
                    title_html = f'<a href="{b_url}" target="_blank" style="{title_style}">{n["書籍タイトル"]}</a>'
                else:
                    title_html = f'<b style="font-size: 1.05rem;">{n["書籍タイトル"]}</b>'

                st.markdown(f"""
                    <div style="line-height: 1.5; margin-bottom: 12px;">
                        {title_html}<br>
                        <div style="color: #666; font-size: 0.85rem; margin-bottom: 8px;">{n['著者名']}</div>
                        <span style="background: #e1f5fe; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; color: #01579b; font-weight: bold; display: inline-block;">
                            推薦: {n_icon} {n_user}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
                
                # 投票ボタン（3列配置）
                v1, v2, v3 = st.columns([1, 1, 1])
                with v1:
                    d1 = is_my_nomination or (1 in v_points) or (current_p > 0)
                    if st.button("+1", key=f"v1_{b_id}", disabled=d1, use_container_width=True):
                        save_and_refresh("votes", {"action": "投票", "book_id": b_id, "points": 1}, "1点投票しました")
                with v2:
                    d2 = is_my_nomination or (2 in v_points) or (current_p > 0)
                    if st.button("+2", key=f"v2_{b_id}", disabled=d2, use_container_width=True, type="primary"):
                        save_and_refresh("votes", {"action": "投票", "book_id": b_id, "points": 2}, "2点投票しました")
                with v3:
                    if current_p > 0:
                        if st.button("消去", key=f"del_{b_id}", use_container_width=True):
                            supabase.table("votes").delete().eq("user_name", st.session_state.USER).eq("book_id", b_id).eq("action", "投票").execute()
                            st.cache_data.clear()
                            st.rerun()

        # --- 3. 自分の投票リセット ---
        st.divider()
        if st.button("自分の投票をすべてリセット", type="secondary", key="reset_all_my_votes", use_container_width=True):
            supabase.table("votes").delete().eq("user_name", st.session_state.USER).eq("action", "投票").execute()
            st.cache_data.clear()
            st.rerun()
            
# --- Tab 3: History (これまでの読書会) ---
with tab3:
    try:
        response = supabase.table("events").select("*, books(*)").execute()
        all_events = pd.DataFrame(response.data)
        
        # 日付処理
        all_events["event_date_dt"] = pd.to_datetime(all_events["event_date"]).dt.date
        all_events["year"] = pd.to_datetime(all_events["event_date"]).dt.year.astype(str)
        
        today = datetime.now().date()
        past_events = all_events[all_events["event_date_dt"] < today]
    except Exception as e:
        st.error(f"データの取得に失敗しました: {e}")
        past_events = pd.DataFrame()

    if not past_events.empty:
        # 1. 重複を除いた年リストを降順（2026, 2025...）で取得
        unique_years = sorted(past_events["year"].unique().tolist(), reverse=True)
        
        # 2. 「すべて」を最後に結合
        year_options = unique_years + ["すべて"]
        
        # 3. リストの先頭（＝一番新しい年）をデフォルトにする
        default_year = unique_years[0]
        
        selected_year = st.pills("開催年で絞り込み", year_options, default=default_year)

        # フィルタリング実行
        if selected_year == "すべて":
            df_history_display = past_events.sort_values("event_date", ascending=False)
        else:
            df_history_display = past_events[past_events["year"] == selected_year].sort_values("event_date", ascending=False)
            
        # --- リスト表示部分 ---
        for _, row in df_history_display.iterrows():
            book = row.get("books", {})
            if not book: continue

            date_str = str(row["event_date"]).replace("-", "/")
            title = book.get("title", "不明")
            author = book.get("author", "不明")
            category = book.get("category", "その他")
            target_url = book.get("url", "")

            # カテゴリ色
            bg_color = "#F5F5F5"

            # HTML組み立て（f-string内でダブルクォーテーションがぶつからないようシングルクォーテーションを使用）
            if target_url:
                title_html = f"<a href='{target_url}' target='_blank' style='text-decoration: none; color: #1E88E5; font-weight: 600; font-size: 1rem;'>{title}</a>"
            else:
                title_html = f"<span style='color: #333; font-weight: 600; font-size: 1rem;'>{title}</span>"

            st.markdown(f"""
            <div style='display: flex; align-items: flex-start; padding: 15px 0; border-bottom: 1px solid #eee; gap: 15px;'>
                <div style='width: 100px; flex-shrink: 0;'>
                    <div style='color: #888; font-size: 0.8rem; margin-bottom: 4px;'>{date_str}</div>
                    <div style='color: #555; font-size: 0.85rem; line-height: 1.2; word-break: break-all;'>{author}</div>
                </div>
                <div style='flex-grow: 1;'>
                    <div style='margin-bottom: 8px; line-height: 1.4;'>
                        {title_html}
                    </div>
                    <div>
                        <span style='background-color: {bg_color}; padding: 2px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; border: 1px solid #ddd; color: #444;'>
                            {category}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("過去の開催履歴はありません。")
                
    # --- 究極の棒グラフ (Altair版：数字を外側に表示) ---
    st.divider()
    st.subheader("📊 カテゴリランキング")

    if not past_events.empty:
        # 1. 重複を排除した「本」のリストを作成
        # event_dateなどは無視して、book_idが同じなら1件とみなす
        unique_books_df = past_events.drop_duplicates(subset=['book_id'])

        # 2. カテゴリを抽出してカウント
        cat_list = [
            str(row.get("books", {}).get("category")) 
            for row in unique_books_df.to_dict('records') 
            if row.get("books")
        ]
        # 無効な値を排除
        cat_list = [c for c in cat_list if c not in ['None', '', 'nan']]

        if cat_list:
            df_counts = pd.Series(cat_list).value_counts().reset_index()
            df_counts.columns = ["カテゴリ", "冊数"]

            # 2. Altairでグラフを作成
            import altair as alt

            bars = alt.Chart(df_counts).mark_bar(
                cornerRadiusTopRight=5,
                cornerRadiusBottomRight=5
            ).encode(
                x=alt.X("冊数:Q", title=None, axis=None),
                y=alt.Y(
                    "カテゴリ:N", 
                    title=None, 
                    sort='-x', 
                    axis=alt.Axis(
                        labelLimit=80,      # 💡 ここで1行の幅を指定（超えると折り返し）
                        labelLineHeight=14, # 💡 行間の高さを指定
                        labelFontSize=12,
                        labelPadding=10
                    )
                ),
                color=alt.Color("カテゴリ:N", legend=None, scale=alt.Scale(scheme='viridis'))
            )

            text = bars.mark_text(
                align='left', baseline='middle', dx=5,
                fontSize=14, fontWeight='bold'
            ).encode(text='冊数:Q')

            chart = (bars + text).properties(
                height=alt.Step(50) # 💡 折り返しを考慮して1件あたりの高さを少し広げました
            ).configure_view(
                strokeOpacity=0
            )

            st.altair_chart(chart, use_container_width=True)
            st.caption("※ 複数月で読んだ本は1冊としてカウントしています")
        else:
            st.info("集計できるカテゴリデータがありません。")



# --- Tab 4: Admin (管理者画面) ---
with tab4:
    if "admin_form_counter" not in st.session_state:
        st.session_state.admin_form_counter = 0
        
    # --- 1. 新規選出セクション（ここがメイン！） ---
    st.subheader("🆕 次回の課題本を確定する")
    nominated_ids = df_active_votes[df_active_votes["action"] == "選出"]["book_id"].unique().tolist()
    nominated_books = df_books[df_books["id"].astype(str).isin([str(x) for x in nominated_ids])]

    if not nominated_books.empty:
        st.info("🗳️ 現在メンバーが選出中の本が表示されています")
        final_list = nominated_books
    else:
        st.warning("現在選出されている本がありません。全リストから表示します。")
        final_list = df_display_books

    with st.form(key=f"admin_form_{st.session_state.admin_form_counter}"):
        st.write("選出リストから次回の本を登録します")
        next_date = st.date_input("読書会の日程") # 個別のkeyは不要になります
        
        if not final_list.empty:
            book_options = {f"[{row['category']}] {row['title']}": row['id'] for _, row in final_list.iterrows()}
            target_label = st.selectbox("課題本を確定", options=list(book_options.keys()))
            target_book_id = book_options[target_label]
        else:
            st.error("選択可能な本がありません。")
            target_book_id = None
        
        if st.form_submit_button("次回予告を確定する", type="primary", use_container_width=True):
            if target_book_id:
                new_event = {
                    "event_date": str(next_date),
                    "book_id": str(target_book_id)
                }
                supabase.table("events").insert(new_event).execute()
                
                st.session_state.admin_form_counter += 1
            
                st.cache_data.clear()
                st.toast("次回予告を更新しました", icon="🚀")
                st.rerun()

    st.divider()

    # --- 2. 継続登録セクション（前回の本をもう一度） ---
    if not df_events.empty:
        # 最新のイベントを1件取得
        last_event = df_events.sort_values("event_date", ascending=False).iloc[0]
        last_book = last_event.get("books", {})
        
        st.subheader("🔁 前回の本を継続する")
        with st.container(border=True):
            st.markdown(f"前回の課題本: **{last_book.get('title', '不明')}**")
            cont_date = st.date_input("継続開催の日付", key="cont_date")
            
            if st.button("この本で次回の予告を作る（継続）", use_container_width=True):
                new_event = {
                    "event_date": str(cont_date),
                    "book_id": str(last_event["book_id"])
                }
                supabase.table("events").insert(new_event).execute()
                st.cache_data.clear()
                st.toast("継続開催を登録しました", icon="🔁")
                st.rerun()

    # --- 3. データの管理 ---
    st.divider()
    st.subheader("🧹 データの管理")
    confirm_reset = st.checkbox("全ユーザーの投票リセットを実行する")
    if st.button("全ユーザーの投票を完全にリセット", type="primary", use_container_width=True, disabled=not confirm_reset):
        try:
            supabase.table("votes").delete().eq("action", "投票").execute()
            st.cache_data.clear()
            st.toast("すべての投票をリセットしました", icon="🙋")
            st.rerun()
        except Exception as e:
            st.error(f"リセットエラー: {e}")

    # Logout
    st.divider()
    if st.button("Logout", use_container_width=True):
        # 💡 セッションの中身をすべて消去する
        st.session_state.clear()
        # 💡 クエリパラメータ（URLの後ろについている名前）も消す
        st.query_params.clear()
        # 💡 強制リロードして最初のログイン画面に戻す
        st.rerun()
        
# 最後に空白
st.markdown("<div style='margin-bottom: 150px;'></div>", unsafe_allow_html=True)
