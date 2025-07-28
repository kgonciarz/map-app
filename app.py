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
m = folium.Map(location=[5, 0], zoom_start=2, tiles="OpenStreetMap")

legend_html = '''
 <div style="
     position: fixed; 
     bottom: 50px; left: 50px; width: 200px; height: auto; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; padding: 10px; border-radius: 5px;">
     <b>🟢 Legend (Role)</b><br>
     <i style="color: red;">●</i> Processor<br>
     <i style="color: blue;">●</i> Trader<br>
     <i style="color: green;">●</i> Trader/Processor<br>
     <i style="color: orange;">●</i> Broker/Trader<br>
     <i style="color: purple;">●</i> Origin/Buyer<br>
     <i style="color: pink;">●</i> Trader/Origin
 </div>
'''
m.get_root().html.add_child(folium.Element(legend_html))


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

# --- Display map with full width ---
st_data = st_folium(m, use_container_width=True, height=600)

# --- Spacer to avoid excessive white space ---
st.markdown("### 📋 List of Companies in the Cocoa Supply Chain")

# --- Table just below the map ---
st.dataframe(df.drop(columns=["MarkerColor"]), use_container_width=True)

