import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map")

# Load your dataset
@st.cache_data
def load_data():
    return pd.read_csv("cocoa_supply_chain.csv")  # or use Excel

df = load_data()

# Sidebar filters
st.sidebar.header("🔍 Filter Companies")

roles = st.sidebar.multiselect("Filter by Role", options=df["Role"].unique(), default=list(df["Role"].unique()))
countries = st.sidebar.multiselect("Filter by Country", options=df["Country"].unique(), default=list(df["Country"].unique()))
min_volume = st.sidebar.slider("Minimum Volume (tons/year)", min_value=0, max_value=int(df["Volume (tons/year)"].max()), value=0, step=5000)

# Apply filters
filtered_df = df[
    (df["Role"].isin(roles)) &
    (df["Country"].isin(countries)) &
    (df["Volume (tons/year)"] >= min_volume)
]

# Show filtered data
st.subheader(f"Filtered Companies: {len(filtered_df)}")
st.dataframe(filtered_df)

# Plot map
fig = px.scatter_geo(
    filtered_df,
    lat="Latitude",
    lon="Longitude",
    text="Company",
    hover_name="Company",
    hover_data={
        "Role": True,
        "Country": True,
        "City": True,
        "Contact Email": True,
        "Volume (tons/year)": True,
    },
    color="Role",
    size="Volume (tons/year)",
    projection="natural earth",
)

fig.update_layout(
    title="Global Cocoa Supply Chain Actors",
    margin={"r":0,"t":30,"l":0,"b":0},
    height=650
)

st.plotly_chart(fig, use_container_width=True)
