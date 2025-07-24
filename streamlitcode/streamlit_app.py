import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---- Load PET Data ----
@st.cache_data
def load_pet_data():
    df = pd.read_excel("PET_flow/Allcountries_export_WITS.xlsx", sheet_name="By-HS6Product")
    df = df[
        (df['Partner'].notna()) &
        (df['Quantity'].notna()) &
        (df['Trade Value 1000USD'].notna()) &
        (df['TradeFlow'].isin(['Export', 'Import']))
    ]
    df = df.rename(columns={'Reporter': 'Country'})
    return df

# ---- Load HS 5407 Data ----
@st.cache_data
def load_5407():
    df = pd.read_excel("/workspaces/PET_tradeflow/PET_flow/total_5407.xlsx")
    df = df.rename(columns={
        "ReporterName": "Country",
        "PartnerName": "Partner",
        "TradeValue in 1000 USD": "Value",
        "TradeFlowName": "TradeFlow"
    })
    df = df[df["TradeFlow"].isin(["Gross Imports", "Gross Exports"])]
    df["TradeFlow"] = df["TradeFlow"].replace({"Gross Imports": "Import", "Gross Exports": "Export"})
    return df

# ---- Coordinates ----
ALL_COORDS = {
    'Austria': (47.5162, 14.5501), 'Germany': (51.1657, 10.4515), 'France': (46.6034, 1.8883),
    'Italy': (41.8719, 12.5674), 'Poland': (51.9194, 19.1451), 'Slovenia': (46.1512, 14.9955),
    'Czech Republic': (49.8175, 15.4730), 'Hungary': (47.1625, 19.5033), 'Netherlands': (52.1326, 5.2913),
    'Belgium': (50.5039, 4.4699), 'Switzerland': (46.8182, 8.2275), 'Spain': (40.4637, -3.7492),
    'Slovakia': (48.6690, 19.6990), 'Croatia': (45.1000, 15.2000), 'Romania': (45.9432, 24.9668),
    'Bulgaria': (42.7339, 25.4858), 'Sweden': (60.1282, 18.6435), 'Denmark': (56.2639, 9.5018),
    'Greece': (39.0742, 21.8243), 'Portugal': (39.3999, -8.2245), 'Finland': (61.9241, 25.7482),
    'Norway': (60.4720, 8.4689), 'Ireland': (53.4129, -8.2439), 'Estonia': (58.5953, 25.0136),
    'Latvia': (56.8796, 24.6032), 'Lithuania': (55.1694, 23.8813), 'United States': (37.0902, -95.7129),
    'Japan': (36.2048, 138.2529), 'China': (35.8617, 104.1954), 'India': (20.5937, 78.9629),
    'Brazil': (-14.2350, -51.9253), 'Mexico': (23.6345, -102.5528), 'Canada': (56.1304, -106.3468),
    'South Korea': (35.9078, 127.7669), 'Australia': (-25.2744, 133.7751), 'Russia': (61.5240, 105.3188),
    'Turkey': (38.9637, 35.2433), 'Ukraine': (48.3794, 31.1656), 'Egypt': (26.8206, 30.8025),
    'South Africa': (-30.5595, 22.9375), 'Singapore': (1.3521, 103.8198), 'Thailand': (15.8700, 100.9925),
    'Indonesia': (-0.7893, 113.9213), 'Malaysia': (4.2105, 101.9758)
}

# ---- Streamlit App ----
st.set_page_config(layout="wide")
page = st.sidebar.radio("Select Page", ["PET Map", "Material 5407"])

if page == "PET Map":
    st.title("PET Trade Balance Map")
    df = load_pet_data()
    # Your existing PET map logic goes here (you can paste from previous version)
    countries = sorted(df['Country'].dropna().unique())
    selected = st.multiselect("Select one or more countries to analyze", countries)
    if not selected:
        st.stop()

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

    # ---- Map ----
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lon=merged['Lon'], lat=merged['Lat'], text=merged['Text'],
        mode='markers',
        marker=dict(size=merged['Size'], color=merged['Color'], line=dict(width=0.5, color='black'),
                    sizemode='area', sizeref=2.*max(merged['Size'])/(40.**2), sizemin=4),
        hoverinfo='text'
    ))
    for country in selected:
        if country in ALL_COORDS:
            lat, lon = ALL_COORDS[country]
            fig.add_trace(go.Scattergeo(
                lon=[lon], lat=[lat], mode='markers+text', marker=dict(size=10, color='blue'),
                text=[country], textposition="top center"
            ))
    fig.update_layout(
        title=f"PET Trade Balance – {', '.join(selected)}",
        geo=dict(scope="world", projection_type="natural earth", showland=True, showcountries=True,
                landcolor='rgb(243, 243, 243)', countrycolor='black')
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---- Sankey ----
    sankey_data = merged.copy()
    sankey_data = sankey_data[sankey_data['Total_Trade'] > 0]
    sankey_summary = sankey_data.groupby('Partner').agg({
        'Import_Quantity': 'sum', 'Export_Quantity': 'sum'
    }).reset_index()
    top_imports = sankey_summary.sort_values(by='Import_Quantity', ascending=False).head(15)
    top_exports = sankey_summary.sort_values(by='Export_Quantity', ascending=False).head(15)
    sankey_subset = pd.concat([top_imports, top_exports]).drop_duplicates()

    left_labels = [f"Import: {p} (kg)" for p in top_imports['Partner']]
    right_labels = [f"Export: {p} (kg)" for p in top_exports['Partner']]
    center_label = f"{', '.join(selected)} (kg)"
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

    # ---- Table ----
    st.subheader("Top 10 Partners by Volume")
    top_partners = merged.groupby('Partner').agg({
        'Import_Quantity': 'sum', 'Export_Quantity': 'sum',
        'Import_Value': 'sum', 'Export_Value': 'sum', 'Total_Trade': 'sum'
    }).sort_values(by='Total_Trade', ascending=False).head(10).reset_index()
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

elif page == "Material 5407":
    df = load_5407()
    st.title("Trade Balance Map for HS Code 5407")
    countries = sorted(df['Country'].dropna().unique())
    selected = st.multiselect("Select one or more countries to analyze", countries)
    if not selected:
        st.stop()

    data = df[df['Country'].isin(selected)]
    imp = data[data['TradeFlow'] == 'Import'].groupby(['Country', 'Partner']).agg({
        'Quantity': 'sum', 'Value': 'sum'
    }).reset_index().rename(columns={'Quantity': 'Import_Quantity', 'Value': 'Import_Value'})

    exp = data[data['TradeFlow'] == 'Export'].groupby(['Country', 'Partner']).agg({
        'Quantity': 'sum', 'Value': 'sum'
    }).reset_index().rename(columns={'Quantity': 'Export_Quantity', 'Value': 'Export_Value'})

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

    # ---- Map ----
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lon=merged['Lon'], lat=merged['Lat'], text=merged['Text'],
        mode='markers',
        marker=dict(size=merged['Size'], color=merged['Color'], line=dict(width=0.5, color='black'),
                    sizemode='area', sizeref=2.*max(merged['Size'])/(40.**2), sizemin=4),
        hoverinfo='text'
    ))
    for country in selected:
        if country in ALL_COORDS:
            lat, lon = ALL_COORDS[country]
            fig.add_trace(go.Scattergeo(
                lon=[lon], lat=[lat], mode='markers+text', marker=dict(size=10, color='blue'),
                text=[country], textposition="top center"
            ))
    fig.update_layout(
        title=f"Trade Balance – HS 5407 – {', '.join(selected)}",
        geo=dict(scope="world", projection_type="natural earth", showland=True, showcountries=True,
                 landcolor='rgb(243, 243, 243)', countrycolor='black')
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---- Sankey ----
    sankey_data = merged.copy()
    sankey_data = sankey_data[sankey_data['Total_Trade'] > 0]
    sankey_summary = sankey_data.groupby('Partner').agg({
        'Import_Quantity': 'sum', 'Export_Quantity': 'sum'
    }).reset_index()
    top_imports = sankey_summary.sort_values(by='Import_Quantity', ascending=False).head(15)
    top_exports = sankey_summary.sort_values(by='Export_Quantity', ascending=False).head(15)
    sankey_subset = pd.concat([top_imports, top_exports]).drop_duplicates()

    left_labels = [f"Import: {p} (kg)" for p in top_imports['Partner']]
    right_labels = [f"Export: {p} (kg)" for p in top_exports['Partner']]
    center_label = f"{', '.join(selected)} (kg)"
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

    # ---- Table ----
    st.subheader("Top 10 Partners by Volume")
    top_partners = merged.groupby('Partner').agg({
        'Import_Quantity': 'sum', 'Export_Quantity': 'sum',
        'Import_Value': 'sum', 'Export_Value': 'sum', 'Total_Trade': 'sum'
    }).sort_values(by='Total_Trade', ascending=False).head(10).reset_index()
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








