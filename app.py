import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map")
st.write("This map shows locations of cocoa-related companies, categorized by role in the supply chain.")

# --- Load cocoa data from Excel ---
@st.cache_data
def load_data():
    return pd.read_excel("cocoa_supply_chain.xlsx")

df = load_data()

# --- Clean and validate coordinates ---
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df.dropna(subset=['Latitude', 'Longitude'], inplace=True)

# --- Altair Map Visualization ---
if not df.empty:
    st.subheader("🗺️ Company Map")

    chart = alt.Chart(df).mark_circle(size=100).encode(
        longitude='Longitude:Q',
        latitude='Latitude:Q',
        color='Role:N',
        tooltip=['Company', 'Role', 'Country', 'City', 'Volume (tons/year)']
    ).properties(
        title="Global Cocoa Supply Chain Actors by Role",
        width='container',
        height=600
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.markdown("✅ The legend is generated automatically from company roles.")

else:
    st.warning("No valid geographic data to display.")

# --- Company Data Table ---
st.subheader("📋 List of Companies in the Cocoa Supply Chain")
st.dataframe(df)
