import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- optional: friendly guard if geopy missing ---
try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
    GEO_AVAILABLE = True
except Exception:
    GEO_AVAILABLE = False

st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map")
st.write("Real geographic map of cocoa companies with interactive colored markers by role.")

# --- Load Excel data ---
@st.cache_data
def load_data():
    return pd.read_excel("cocoa_supply_chain (2).xlsx")

df = load_data()

# --- Validate required columns ---
required_cols = {"Company", "Role", "Country", "City"}
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing required column(s) in Excel: {', '.join(missing)}")
    st.stop()

# --- Build a location string from City + Country ---
df["City"] = df["City"].astype(str).str.strip()
df["Country"] = df["Country"].astype(str).str.strip()
df["location_str"] = (df["City"] + ", " + df["Country"]).str.replace(r"^,\s*|,\s*$", "", regex=True)

# --- Geocoder (cached resource) ---
@st.cache_resource
def get_geocoder():
    geolocator = Nominatim(user_agent="cocoa-map-app", timeout=10)
    return RateLimiter(geolocator.geocode, min_delay_seconds=1)

# --- Geocode helper (cache results for the session) ---
@st.cache_data
def geocode_locations(unique_locations):
    """Return a dict {location_str: (lat, lon)} for the given unique list."""
    results = {}
    if not GEO_AVAILABLE:
        return {loc: (None, None) for loc in unique_locations}

    geocode = get_geocoder()
    for loc in unique_locations:
        try:
            hit = geocode(loc)
            if hit:
                results[loc] = (hit.latitude, hit.longitude)
            else:
                results[loc] = (None, None)
        except Exception:
            results[loc] = (None, None)
    return results

# --- Sidebar: Geocoding control ---
st.sidebar.markdown("### 📍 Locations")
if not GEO_AVAILABLE:
    st.sidebar.error("`geopy` is not installed. Add `geopy` to requirements.txt and redeploy.")
    st.stop()

do_geocode = st.sidebar.button("Geocode City + Country → Coordinates")

# Only geocode on demand (prevents long startup)
if do_geocode:
    with st.spinner("Geocoding cities… (cached for this session)"):
        lookup = geocode_locations(df["location_str"].dropna().unique().tolist())
    st.success("Geocoding finished. You can change filters or rerun without waiting again.")
else:
    # If we already have a cached result from a previous click this session,
    # the call is instant; otherwise coordinates will be None.
    lookup = geocode_locations(df["location_str"].dropna().unique().tolist())

# Map coordinates back
df["Latitude"]  = df["location_str"].map(lambda x: lookup.get(x, (None, None))[0])
df["Longitude"] = df["location_str"].map(lambda x: lookup.get(x, (None, None))[1])

# Drop rows where we couldn’t geocode
df = df.dropna(subset=["Latitude", "Longitude"]).copy()
if df.empty:
    st.warning("No rows have coordinates yet. Click the **Geocode** button in the sidebar.")
    st.stop()

# --- Normalize "Customer Y/N" to Yes/No (blank -> No) ---
if "Customer (Y/N)" in df.columns:
    raw = df["Customer (Y/N)"]
    df["Customer"] = (
        raw.fillna("")
           .astype(str).str.strip().str.lower()
           .replace({"": "no", "nan": "no"})
           .map({
               "y": "Yes", "yes": "Yes", "1": "Yes", "true": "Yes",
               "n": "No", "no": "No", "0": "No", "false": "No"
           })
           .fillna("No")
    )
else:
    if "Customer" not in df.columns:
        df["Customer"] = "No"

# --- Role to color mapping ---
role_colors = {
    "Exporter/Trader": "blue",
    "Processor/Manufacturer": "red",
    "Support & Services": "green",
    "N/A": "gray",
}
df["MarkerColor"] = df["Role"].apply(lambda r: role_colors.get(str(r), "gray"))

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filter Companies")

# Ensure volume numeric
df["Volume (tons/year)"] = pd.to_numeric(df.get("Volume (tons/year)"), errors='coerce')

# Role filter
available_roles = sorted(df["Role"].dropna().astype(str).unique())
role_options = ["All"] + available_roles
selected_roles = st.sidebar.multiselect("Select Role(s)", role_options, default=["All"])
filtered_roles = available_roles if "All" in selected_roles or not selected_roles else selected_roles

# Country filter
available_countries = sorted(df["Country"].dropna().astype(str).unique())
country_options = ["All"] + available_countries
selected_countries = st.sidebar.multiselect("Select Country(s)", country_options, default=["All"])
filtered_countries = available_countries if "All" in selected_countries or not selected_countries else selected_countries

# Company filter
available_companies = sorted(df["Company"].dropna().astype(str).unique())
company_options = ["All"] + available_companies
selected_companies = st.sidebar.multiselect("Select Company(s)", company_options, default=["All"])
filtered_companies = available_companies if "All" in selected_companies or not selected_companies else selected_companies

# Customer filter
customer_choice = st.sidebar.radio("Customer?", ["All", "Yes", "No"], index=0)

# Volume slider (robust to all-NaN)
vmin = df["Volume (tons/year)"].min(skipna=True)
vmax = df["Volume (tons/year)"].max(skipna=True)
if pd.isna(vmin) or pd.isna(vmax):
    vmin, vmax = 0, 0
volume_threshold = st.sidebar.slider("Minimum Volume (tons/year)",
                                     int(vmin), int(vmax), value=int(vmin), step=10_000)

# Apply filters
filtered_df = df[
    (df["Role"].astype(str).isin(filtered_roles)) &
    (df["Country"].astype(str).isin(filtered_countries)) &
    (df["Company"].astype(str).isin(filtered_companies)) &
    ((df["Volume (tons/year)"].isna()) | (df["Volume (tons/year)"] >= volume_threshold))
].copy()

if customer_choice != "All":
    filtered_df = filtered_df[filtered_df["Customer"] == customer_choice].copy()

if filtered_df.empty:
    st.info("No results for the selected filters.")
    st.stop()

# --- Create Folium map centered on cocoa belt ---
m = folium.Map(location=[10, 0], zoom_start=2, tiles="CartoDB Positron")

# --- Legend ---
legend_html = '''
 <div style="
     position: fixed;
     bottom: 50px; left: 50px; width: 230px; height: auto;
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; padding: 10px; border-radius: 5px;">
     <b>🟢 Legend (Role)</b><br>
     <i style="color: blue;">●</i> Exporter/Trader<br>
     <i style="color: red;">●</i> Processor/Manufacturer<br>
     <i style="color: green;">●</i> Support & Services<br>
     <i style="color: gray;">●</i> N/A
 </div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# --- Marker cluster ---
marker_cluster = MarkerCluster().add_to(m)

for _, row in filtered_df.iterrows():
    try:
        volume_formatted = f"{int(row['Volume (tons/year)']):,}"
    except Exception:
        volume_formatted = row['Volume (tons/year)']

    popup_html = f"""
    <b>{row['Company']}</b><br>
    Role: {row['Role']}<br>
    Location: {row['City']}, {row['Country']}<br>
    Volume: {volume_formatted} tons<br>
    Customer: {row['Customer']}<br>
    Email: {row.get('Contact Email', '')}
    """

    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=popup_html,
        icon=folium.Icon(color=row["MarkerColor"])
    ).add_to(marker_cluster)

# --- Display map ---
st_folium(m, use_container_width=True, height=600)

# --- Charts ---
import plotly.express as px

st.markdown("### 📊 Cocoa Supply Chain Analytics")

filtered_df["Volume (tons/year)"] = pd.to_numeric(filtered_df["Volume (tons/year)"], errors='coerce')

# 1. Volume by Role
volume_by_role = (
    filtered_df.groupby("Role", dropna=False)["Volume (tons/year)"]
    .sum(min_count=1)
    .sort_values(ascending=False)
    .reset_index()
    .head(5)
)
fig_role = px.bar(
    volume_by_role, x="Role", y="Volume (tons/year)",
    title="Total Volume by Role",
    labels={"Volume (tons/year)": "Volume (tons/year)", "Role": "Role"}
)
st.plotly_chart(fig_role, use_container_width=True)

# 2. Volume by Country
volume_by_country = (
    filtered_df.groupby("Country", dropna=False)["Volume (tons/year)"]
    .sum(min_count=1)
    .sort_values(ascending=False)
    .reset_index()
)
fig_country = px.pie(
    volume_by_country, names="Country", values="Volume (tons/year)",
    title="Volume Distribution by Country"
)
st.plotly_chart(fig_country, use_container_width=True)

# 3. Top 10 Companies by Volume
top_companies = (
    filtered_df[["Company", "Volume (tons/year)"]]
    .dropna()
    .sort_values(by="Volume (tons/year)", ascending=False)
    .head(10)
)
fig_top10 = px.bar(
    top_companies, x="Company", y="Volume (tons/year)",
    title="Top 10 Companies by Volume",
    labels={"Volume (tons/year)": "Volume", "Company": "Company"},
)
st.plotly_chart(fig_top10, use_container_width=True)

# --- Table ---
st.markdown("### 📋 List of Companies in the Cocoa Supply Chain")
filtered_df["Volume (formatted)"] = filtered_df["Volume (tons/year)"].apply(
    lambda x: f"{int(x):,}" if pd.notnull(x) and isinstance(x, (int, float)) else x
)
st.dataframe(
    filtered_df[[
        "Company", "Role", "Country", "City", "Customer", "Contact Email",
        "Volume (formatted)", "Latitude", "Longitude", "Notes"
    ]],
    use_container_width=True
)
