import streamlit as st

st.set_page_config(page_title="Emergency Access Peru", layout="wide")

tab1, tab2, tab3, tab4 = st.tabs([
    "District Rankings",
    "Geospatial Map",
    "Health Facilities",
    "Statistical Comparison",
])

with tab1:
    st.header("District Rankings")
    st.info("Coming soon.")

with tab2:
    st.header("Geospatial Map")
    st.info("Coming soon.")

with tab3:
    st.header("Health Facilities")
    st.info("Coming soon.")

with tab4:
    st.header("Statistical Comparison")
    st.info("Coming soon.")
