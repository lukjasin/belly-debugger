import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
APP_NAME = os.getenv("APP_NAME", "Belly-Debugger")

st.set_page_config(page_title=APP_NAME, page_icon="📉")

pg = st.navigation([
    st.Page("pages/add_meal.py",        title="Add Meal",                icon="📉"),
    st.Page("pages/edit_records.py",    title="Edit Records",            icon="✏️"),
    st.Page("pages/body_weight.py",     title="Register Body Weight",    icon="⚖️"),
])
pg.run()