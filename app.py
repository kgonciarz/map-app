import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map (Folium)")
st.write("Real geographic map of cocoa companies with interactive colored markers by role.")

# --- Load Excel data ---
@st.cache_data
def load_data():
    return pd.read_excel("cocoa_supply_chain.xlsx")

df = load_data()

# --- Clean coordinates ---
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df.dropna(subset=['Latitude', 'Longitude'], inplace=True)

# --- Role to color mapping ---
role_colors = {
    "Processor": "red",
    "Trader": "blue",
    "Trader/Processor": "green",
    "Broker/Trader": "orange",
    "Origin/Buyer": "purple",
    "Trader/Origin": "pink",
}
df["MarkerColor"] = df["Role"].apply(lambda r: role_colors.get(r, "gray"))

# --- Create Folium map centered on cocoa belt ---
m = folium.Map(location=[5, 0], zoom_start=2.5)

marker_cluster = MarkerCluster().add_to(m)

# --- Add markers to map ---
for _, row in df.iterrows():
    popup_html = f"""
    <b>{row['Company']}</b><br>
    Role: {row['Role']}<br>
    Location: {row['City']}, {row['Country']}<br>
    Volume: {row['Volume (tons/year)']} tons<br>
    Email: {row['Contact Email']}
    """
    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=popup_html,
        icon=folium.Icon(color=row["MarkerColor"])
    ).add_to(marker_cluster)

# --- Display the map ---
st_data = st_folium(m, width=1200, height=600)

# --- Display the data table ---
st.subheader("📋 List of Companies in the Cocoa Supply Chain")
st.dataframe(df.drop(columns=["MarkerColor"]))
