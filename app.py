import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map (Improved)")

@st.cache_data
def load_data():
    return pd.read_csv("cocoa_supply_chain.csv")

df = load_data()

# Sidebar filters
roles = st.sidebar.multiselect("Role", df["Role"].unique(), default=df["Role"].unique())
min_volume = st.sidebar.slider("Minimum Volume", 0, int(df["Volume (tons/year)"].max()), 0, 5000)

filtered_df = df[(df["Role"].isin(roles)) & (df["Volume (tons/year)"] >= min_volume)]

# Map Layer
layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered_df,
    get_position='[Longitude, Latitude]',
    get_radius="Volume (tons/year) / 1000",  # Adjust size by volume
    get_fill_color="[200, 30, 0, 160]",
    pickable=True,
)

# Map View
view_state = pdk.ViewState(
    latitude=0,
    longitude=0,
    zoom=1.3,
    pitch=0
)

# Tooltip
tooltip = {
    "html": "<b>{Company}</b><br>{Role}<br>{Country}, {City}<br>Volume: {Volume (tons/year)} tons",
    "style": {"backgroundColor": "steelblue", "color": "white"}
}

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip
))
