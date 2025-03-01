from utils.summary import generate_summary
from utils.utilities import utilities_ui
import streamlit as st

# Main Streamlit App
st.title("SQLite Reading Summary Generator")

# Tabs for navigation
tabs = st.tabs(["Summary"])

with tabs[0]:
    st.write("### Summary")
    generate_summary()
