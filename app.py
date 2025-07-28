import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map")
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
m = folium.Map(location=[10, 0], zoom_start=2, tiles="CartoDB Positron")

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

for _, row in df.iterrows():
    # Format volume with commas
    try:
        volume_formatted = f"{int(row['Volume (tons/year)']):,}"
    except:
        volume_formatted = row['Volume (tons/year)']  # fallback if it's not a number

    popup_html = f"""
    <b>{row['Company']}</b><br>
    Role: {row['Role']}<br>
    Location: {row['City']}, {row['Country']}<br>
    Volume: {volume_formatted} tons<br>
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
df["Volume (formatted)"] = df["Volume (tons/year)"].apply(
    lambda x: f"{int(x):,}" if pd.notnull(x) and isinstance(x, (int, float)) else x
)

# --- Table just below the map ---
st.dataframe(df.drop(columns=["MarkerColor"]), use_container_width=True)
st.dataframe(
    df[[
        "Company", "Role", "Country", "City", "Contact Email", 
        "Volume (formatted)", "Latitude", "Longitude", "Notes"
    ]],
    use_container_width=True
)

