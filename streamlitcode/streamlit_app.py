import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from geopy.geocoders import Nominatim

# ---- Load Data ----
@st.cache_data
def load_data():
    df = pd.read_excel("PET_flow/Allcountries_export_WITS.xlsx", sheet_name="By-HS6Product")
    df = df[
        (df['Partner'].notna()) &
        (df['Quantity'].notna()) &
        (df['Trade Value 1000USD'].notna()) &
        (df['TradeFlow'].isin(['Export', 'Import']))
    ]
    df = df.rename(columns={'Reporter': 'Country'})
    return df

df = load_data()

# ---- Get All Country Coordinates ----
geolocator = Nominatim(user_agent="pet_trade_locator")
@st.cache_data
def get_coords(country):
    try:
        location = geolocator.geocode(country)
        return (location.latitude, location.longitude)
    except:
        return (None, None)

all_countries = pd.unique(df[['Country', 'Partner']].values.ravel('K'))
ALL_COORDS = {c: get_coords(c) for c in all_countries}

# ---- UI ----
st.set_page_config(layout="wide")
st.title("PET Trade Balance Map (Europe + World)")
countries = sorted(df['Country'].dropna().unique())
selected = st.multiselect("Select one or more countries to analyze", countries)
if not selected:
    st.stop()

# ---- Aggregate Data ----
data = df[df['Country'].isin(selected)]
imp = data[data['TradeFlow'] == 'Import'].groupby(['Country', 'Partner']).agg({
    'Quantity': 'sum', 'Trade Value 1000USD': 'sum'
}).reset_index().rename(columns={'Quantity': 'Import_Quantity', 'Trade Value 1000USD': 'Import_Value'})

exp = data[data['TradeFlow'] == 'Export'].groupby(['Country', 'Partner']).agg({
    'Quantity': 'sum', 'Trade Value 1000USD': 'sum'
}).reset_index().rename(columns={'Quantity': 'Export_Quantity', 'Trade Value 1000USD': 'Export_Value'})

merged = pd.merge(imp, exp, on=['Country', 'Partner'], how='outer').fillna(0)
merged['Balance'] = merged['Export_Quantity'] - merged['Import_Quantity']

merged['Direction'] = merged['Balance'].apply(lambda x: 'Export Surplus' if x > 0 else ('Import Surplus' if x < 0 else 'Balanced'))
merged['Color'] = merged['Direction'].map({'Export Surplus': 'green', 'Import Surplus': 'red', 'Balanced': 'gray'})
merged['Total_Trade'] = merged['Export_Quantity'] + merged['Import_Quantity']
merged['Size'] = merged['Total_Trade']**0.5 / 100

merged['Lat'] = merged['Partner'].map(lambda c: ALL_COORDS.get(c, (None, None))[0])
merged['Lon'] = merged['Partner'].map(lambda c: ALL_COORDS.get(c, (None, None))[1])
merged['Text'] = merged.apply(lambda r: f"{r['Partner']}<br>Export: {r['Export_Quantity']:,.0f} Kg<br>Import: {r['Import_Quantity']:,.0f} Kg<br>Balance: {r['Balance']:,.0f} Kg", axis=1)
merged = merged.dropna(subset=['Lat', 'Lon'])

# ---- Plot Map ----
fig = go.Figure()
fig.add_trace(go.Scattergeo(
    lon=merged['Lon'], lat=merged['Lat'], text=merged['Text'],
    mode='markers',
    marker=dict(
        size=merged['Size'], color=merged['Color'], line=dict(width=0.5, color='black'),
        sizemode='area', sizeref=2.*max(merged['Size'])/(40.**2), sizemin=4
    ),
    hoverinfo='text'
))

for country in selected:
    if country in ALL_COORDS:
        lat, lon = ALL_COORDS[country]
        fig.add_trace(go.Scattergeo(
            lon=[lon], lat=[lat], mode='markers+text',
            marker=dict(size=10, color='blue'),
            text=[country], textposition="top center"
        ))

fig.update_layout(
    title=f"PET Trade Balance – {', '.join(selected)}",
    geo=dict(
        scope="world",
        projection_type="natural earth",
        showland=True,
        showcountries=True,
        landcolor='rgb(243, 243, 243)',
        countrycolor='black',
    )
)

st.plotly_chart(fig, use_container_width=True)

# ---- Sankey Diagram (Top 15 Imports and Exports) ----
sankey_data = merged.copy()
sankey_data = sankey_data[sankey_data['Total_Trade'] > 0]

top_imports = sankey_data.sort_values(by='Import_Quantity', ascending=False).head(15)
top_exports = sankey_data.sort_values(by='Export_Quantity', ascending=False).head(15)

sankey_subset = pd.concat([top_imports, top_exports]).drop_duplicates()

left_labels = [f"Import: {p} (kg)" for p in top_imports['Partner']]
right_labels = [f"Export: {p} (kg)" for p in top_exports['Partner']]
center_label = f"{selected[0]} (kg)"
labels = left_labels + [center_label] + right_labels
label_map = {label: i for i, label in enumerate(labels)}

sources = [label_map[f"Import: {r['Partner']} (kg)"] for _, r in top_imports.iterrows()] + \
          [label_map[center_label]] * len(top_exports)

targets = [label_map[center_label]] * len(top_imports) + \
          [label_map[f"Export: {r['Partner']} (kg)"] for _, r in top_exports.iterrows()]

values = list(top_imports['Import_Quantity']) + list(top_exports['Export_Quantity'])

sankey_fig = go.Figure(data=[go.Sankey(
    node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels),
    link=dict(source=sources, target=targets, value=values)
)])

st.subheader("Top 15 Import/Export Flows (in kg) – Sankey Diagram")
st.plotly_chart(sankey_fig, use_container_width=True)

# ---- Top 10 Partner Summary ----
st.subheader("Top 10 Partners by Volume")
top_partners = merged.groupby('Partner').agg({
    'Import_Quantity': 'sum',
    'Export_Quantity': 'sum',
    'Import_Value': 'sum',
    'Export_Value': 'sum',
    'Total_Trade': 'sum'
}).sort_values(by='Total_Trade', ascending=False).head(10).reset_index()

# Rename columns to include units
top_partners = top_partners.rename(columns={
    'Import_Quantity': 'Import Quantity (KG)',
    'Export_Quantity': 'Export Quantity (KG)',
    'Import_Value': 'Import Value (1000 $)',
    'Export_Value': 'Export Value (1000 $)',
    'Total_Trade': 'Total Trade ($)'
})

st.dataframe(top_partners.style.format({
    'Import Quantity (KG)': "{:.0f}",
    'Export Quantity (KG)': "{:.0f}",
    'Import Value (1000 $)': "${:,.0f}",
    'Export Value (1000 $)': "${:,.0f}",
    'Total Trade ($)': "{:.0f}"
}))





