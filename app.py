import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


st.set_page_config(layout="wide")
st.title("🌍 Cocoa Supply Chain Actors Map")
st.write("Real geographic map of cocoa companies with interactive colored markers by role.")

# --- Load Excel data ---
@st.cache_data
def load_data():
    return pd.read_excel("cocoa_supply_chain (2).xlsx")

df = load_data()

@st.cache_resource
def get_geocoder():
    geolocator = Nominatim(user_agent="cocoa-map-app", timeout=10)
    # Nominatim usage policy: be gentle; 1 rps
    return RateLimiter(geolocator.geocode, min_delay_seconds=1)

@st.cache_data
def load_geocode_cache(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=["place", "Latitude", "Longitude"])

def save_geocode_cache(df_cache: pd.DataFrame, path: str):
    df_cache.to_csv(path, index=False)


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
    df["Customer"] = "No"

# --- Clean coordinates ---
# --- Build City, Country key ---
df["City"] = df.get("City", "").astype(str).str.strip()
df["Country"] = df.get("Country", "").astype(str).str.strip()
df["place_key"] = (df["City"] + ", " + df["Country"]).str.replace(r"^,\s*|,\s*$", "", regex=True)

# --- Load existing geocode cache and attach coords ---
geo_cache = load_geocode_cache(GEOCODE_CACHE_PATH)
cache_map = dict(zip(geo_cache["place"], zip(geo_cache["Latitude"], geo_cache["Longitude"])))
df["Latitude"]  = df["place_key"].map(lambda p: cache_map.get(p, (np.nan, np.nan))[0])
df["Longitude"] = df["place_key"].map(lambda p: cache_map.get(p, (np.nan, np.nan))[1])

st.sidebar.markdown("---")
st.sidebar.write("📍 Geocoding")
do_geocode = st.sidebar.button("Geocode missing City + Country")
show_fast_map = st.sidebar.checkbox("Use fast map (pydeck)", value=False,
                                    help="Faster for many points; no Folium popups.")

if do_geocode:
    with st.spinner("Geocoding new cities… (cached)"):
        geocode = get_geocoder()

        # Only geocode unique places not already cached
        missing_places = (df.loc[df["Latitude"].isna() | df["Longitude"].isna(), "place_key"]
                            .dropna().unique().tolist())
        new_rows = []
        for p in missing_places:
            try:
                loc = geocode(p)
                if loc:
                    new_rows.append({"place": p, "Latitude": loc.latitude, "Longitude": loc.longitude})
                else:
                    new_rows.append({"place": p, "Latitude": np.nan, "Longitude": np.nan})
            except Exception:
                new_rows.append({"place": p, "Latitude": np.nan, "Longitude": np.nan})

        if new_rows:
            geo_cache = pd.concat([geo_cache, pd.DataFrame(new_rows)], ignore_index=True)\
                         .drop_duplicates(subset=["place"], keep="last")
            save_geocode_cache(geo_cache, GEOCODE_CACHE_PATH)

        # Reattach updated cache
        cache_map = dict(zip(geo_cache["place"], zip(geo_cache["Latitude"], geo_cache["Longitude"])))
        df["Latitude"]  = df["place_key"].map(lambda p: cache_map.get(p, (np.nan, np.nan))[0])
        df["Longitude"] = df["place_key"].map(lambda p: cache_map.get(p, (np.nan, np.nan))[1])

# Drop rows we still can't place
df.dropna(subset=["Latitude", "Longitude"], inplace=True)



# --- Role to color mapping ---
role_colors = {
    "Exporter/Trader": "blue",
    "Processor/Manufacturer": "red",
    "Support & Services": "green",
    "N/A": "gray",
}
df["MarkerColor"] = df["Role"].apply(lambda r: role_colors.get(r, "gray"))

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filter Companies")

# --- Ensure volume is numeric and handle missing values ---
df["Volume (tons/year)"] = pd.to_numeric(df["Volume (tons/year)"], errors='coerce')

# Role filter
available_roles = sorted(df["Role"].dropna().unique())
role_options = ["All"] + available_roles
selected_roles = st.sidebar.multiselect("Select Role(s)", role_options, default=["All"])
filtered_roles = available_roles if "All" in selected_roles or not selected_roles else selected_roles

# Country filter
available_countries = sorted(df["Country"].dropna().unique())
country_options = ["All"] + available_countries
selected_countries = st.sidebar.multiselect("Select Country(s)", country_options, default=["All"])
filtered_countries = available_countries if "All" in selected_countries or not selected_countries else selected_countries

# Company filter
available_companies = sorted(df["Company"].dropna().unique())
company_options = ["All"] + available_companies
selected_companies = st.sidebar.multiselect("Select Company(s)", company_options, default=["All"])
filtered_companies = available_companies if "All" in selected_companies or not selected_companies else selected_companies

# ✅ MOVED: Customer filter goes with the other sidebar controls
customer_choice = st.sidebar.radio("Customer?", ["All", "Yes", "No"], index=0)  # NEW

# Volume slider (handle only rows with numeric volume)
volume_min = int(df["Volume (tons/year)"].min(skipna=True))
volume_max = int(df["Volume (tons/year)"].max(skipna=True))
volume_threshold = st.sidebar.slider("Minimum Volume (tons/year)", volume_min, volume_max, value=volume_min, step=10000)

# Apply filters
filtered_df = df[
    (df["Role"].isin(filtered_roles)) &
    (df["Country"].isin(filtered_countries)) &
    (df["Company"].isin(filtered_companies)) &
    ((df["Volume (tons/year)"].isna()) | (df["Volume (tons/year)"] >= volume_threshold))
].copy()

# ✅ NEW: actually apply the Customer filter to the selection
if customer_choice != "All":
    filtered_df = filtered_df[filtered_df["Customer"] == customer_choice].copy()

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
    except:
        volume_formatted = row['Volume (tons/year)']

    popup_html = f"""
    <b>{row['Company']}</b><br>
    Role: {row['Role']}<br>
    Location: {row['City']}, {row['Country']}<br>
    Volume: {volume_formatted} tons<br>
    Customer: {row['Customer']}<br>
    Email: {row['Contact Email']}
    """

    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=popup_html,
        icon=folium.Icon(color=row["MarkerColor"])
    ).add_to(marker_cluster)

# --- Display map ---
st_data = st_folium(m, use_container_width=True, height=600)

import plotly.express as px

st.markdown("### 📊 Cocoa Supply Chain Analytics")

# --- Ensure volume is numeric ---
filtered_df["Volume (tons/year)"] = pd.to_numeric(filtered_df["Volume (tons/year)"], errors='coerce')

# --- 1. Volume by Role (Bar Chart) ---
volume_by_role = (
    filtered_df.groupby("Role")["Volume (tons/year)"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
    .head(5)
)
fig_role = px.bar(
    volume_by_role,
    x="Role",
    y="Volume (tons/year)",
    title="Total Volume by Role",
    labels={"Volume (tons/year)": "Volume (tons/year)", "Role": "Role"}
)
st.plotly_chart(fig_role, use_container_width=True)

# --- 2. Volume by Country (Pie Chart) ---
volume_by_country = (
    filtered_df.groupby("Country")["Volume (tons/year)"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)
fig_country = px.pie(
    volume_by_country,
    names="Country",
    values="Volume (tons/year)",
    title="Volume Distribution by Country"
)
st.plotly_chart(fig_country, use_container_width=True)

# --- 3. Top 10 Companies by Volume ---
top_companies = (
    filtered_df[["Company", "Volume (tons/year)"]]
    .dropna()
    .sort_values(by="Volume (tons/year)", ascending=False)
    .head(10)
)
fig_top10 = px.bar(
    top_companies,
    x="Company",
    y="Volume (tons/year)",
    title="Top 10 Companies by Volume",
    labels={"Volume (tons/year)": "Volume", "Company": "Company"},
)
st.plotly_chart(fig_top10, use_container_width=True)

# --- Table Header ---
st.markdown("### 📋 List of Companies in the Cocoa Supply Chain")

# --- Format volume ---
filtered_df["Volume (formatted)"] = filtered_df["Volume (tons/year)"].apply(
    lambda x: f"{int(x):,}" if pd.notnull(x) and isinstance(x, (int, float)) else x
)

# --- Display filtered table ---
st.dataframe(
    filtered_df[[
        "Company", "Role", "Country", "City", "Customer", "Contact Email",
        "Volume (formatted)", "Latitude", "Longitude", "Notes"
    ]],
    use_container_width=True
)
