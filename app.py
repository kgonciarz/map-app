import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map (Improved)")

@st.cache_data
def load_data():
    df = pd.read_csv("cocoa_supply_chain.csv")
    df["Radius"] = df["Volume (tons/year)"] / 1000  # For map sizing
    return df

df = load_data()

# --- Sidebar filters ---
st.sidebar.header("🔍 Filter Companies")

roles = st.sidebar.multiselect("Role", df["Role"].unique(), default=list(df["Role"].unique()))
min_volume = st.sidebar.slider("Minimum Volume (tons/year)", 0, int(df["Volume (tons/year)"].max()), 0, step=10000)

# --- Apply filters ---
filtered_df = df[
    (df["Role"].isin(roles)) &
    (df["Volume (tons/year)"] >= min_volume)
]

# --- Color mapping based on role ---
role_colors = {
    "Processor": [255, 0, 0],            # red
    "Trader": [0, 128, 255],             # blue
    "Trader/Processor": [0, 200, 0],     # green
    "Broker/Trader": [255, 165, 0],      # orange
    "Origin/Buyer": [128, 0, 128],       # purple
    "Trader/Origin": [255, 0, 255],      # pink
}
filtered_df["Color"] = filtered_df["Role"].apply(lambda role: role_colors.get(role, [150, 150, 150]))

# --- Pydeck map layer ---
layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered_df,
    get_position='[Longitude, Latitude]',
    get_radius="Radius",
    get_fill_color="Color",
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=10,         # Center near West Africa
    longitude=0,
    zoom=3.5,            # Tighter zoom
    min_zoom=2,
    max_zoom=4.5,        # Restrict zoom-out to prevent infinite wrapping
    pitch=0
)


tooltip = {
    "html": """
    <b>{Company}</b><br>
    {Role}<br>
    {City}, {Country}<br>
    Volume: {Volume (tons/year)} tons
    """,
    "style": {"backgroundColor": "black", "color": "white"}
}

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip
))

# --- Legend ---
st.markdown("### 🗂️ Role Legend (Point Colors)")
for role, color in role_colors.items():
    st.markdown(f"<span style='color: rgb({color[0]}, {color[1]}, {color[2]});'>●</span> {role}", unsafe_allow_html=True)

# --- Table ---
st.markdown("### 📋 List of Companies in the Cocoa Supply Chain")
st.dataframe(filtered_df.drop(columns=["Radius", "Color"]))
