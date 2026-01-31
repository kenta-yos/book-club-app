import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd

st.set_page_config(page_title="読書会")

# 接続（名前を指定しない自動モード）
conn = st.connection("gsheets", type=GSheetsConnection)

# データ読み込み
try:
    df_b = conn.read(worksheet="booklist", ttl=5)
    st.write("### 🎉 接続成功！本の一覧を表示します")
    st.dataframe(df_b)
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
