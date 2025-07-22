import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
st.write("Current Working Directory:", os.getcwd())
st.write("Files in current folder:", os.listdir())
st.write("Files in ../PET_flow:", os.listdir("../PET_flow"))
# ---- Load Data ----
@st.cache_data
def load_data():
    import os
    st.write("Files in PET_flow:", os.listdir("PET_flow"))
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

# ---- Country Coordinates ----
COUNTRY_COORDS = {
    'Austria': (47.5162, 14.5501), 'Germany': (51.1657, 10.4515), 'France': (46.6034, 1.8883),
    'Italy': (41.8719, 12.5674), 'Poland': (51.9194, 19.1451), 'Slovenia': (46.1512, 14.9955),
    'Czech Republic': (49.8175, 15.4730), 'Hungary': (47.1625, 19.5033), 'Netherlands': (52.1326, 5.2913),
    'Belgium': (50.5039, 4.4699), 'Switzerland': (46.8182, 8.2275), 'Spain': (40.4637, -3.7492),
    'Slovakia': (48.6690, 19.6990), 'Croatia': (45.1000, 15.2000), 'Romania': (45.9432, 24.9668),
    'Bulgaria': (42.7339, 25.4858), 'Sweden': (60.1282, 18.6435), 'Denmark': (56.2639, 9.5018),
    'Greece': (39.0742, 21.8243), 'Portugal': (39.3999, -8.2245), 'Finland': (61.9241, 25.7482),
    'Norway': (60.4720, 8.4689), 'Ireland': (53.4129, -8.2439), 'Estonia': (58.5953, 25.0136),
    'Latvia': (56.8796, 24.6032), 'Lithuania': (55.1694, 23.8813)
}

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

merged['Lat'] = merged['Partner'].map(lambda c: COUNTRY_COORDS.get(c, (None, None))[0])
merged['Lon'] = merged['Partner'].map(lambda c: COUNTRY_COORDS.get(c, (None, None))[1])
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

# Mark origin countries
for country in selected:
    if country in COUNTRY_COORDS:
        lat, lon = COUNTRY_COORDS[country]
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
