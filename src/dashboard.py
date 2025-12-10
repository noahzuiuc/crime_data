import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Crime Data Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DATA LOADING FUNCTION ---
@st.cache_data
def load_data():
    # Adjust this path if your folder structure is different
    # Assuming script is in 'src' and data is in sibling folder 'Combined Data'
    folder_path = os.path.join(os.path.dirname(__file__), '..', 'Combined Data')
    
    # List of specific files based on your screenshot
    files = [
        "aggravated-assault.csv",
        "grand-theft-auto.csv",
        "homicide.csv",
        "larceny.csv",
        "robbery.csv",
        "sexual-assault.csv"
    ]
    
    all_data = []
    
    # Check if directory exists
    if not os.path.exists(folder_path):
        st.error(f"⚠️ Data folder not found at: {folder_path}. Please check your folder structure.")
        return pd.DataFrame()

    for filename in files:
        file_path = os.path.join(folder_path, filename)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                
                # Derive 'Crime Type' from the filename
                # e.g., "grand-theft-auto.csv" -> "Grand Theft Auto"
                crime_type = filename.replace('.csv', '').replace('-', ' ').title()
                df['Crime Type'] = crime_type
                
                all_data.append(df)
            except Exception as e:
                st.warning(f"Could not read {filename}: {e}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()

# --- LOAD DATA ---
df = load_data()

# --- HEADER ---
st.title("📊 Crime Statistics Dashboard")
st.markdown("Visualize trends across different cities and crime categories over time.")
st.markdown("---")

if df.empty:
    st.warning("No data loaded. Please ensure your CSV files are in the 'Combined Data' folder next to the 'src' folder.")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Options")

# 1. City Filter
all_cities = sorted(df['city'].unique())
selected_cities = st.sidebar.multiselect(
    "Select Cities",
    all_cities,
    default=all_cities
)

# 2. Crime Type Filter
all_types = sorted(df['Crime Type'].unique())
selected_types = st.sidebar.multiselect(
    "Select Crime Types",
    all_types,
    default=all_types # Default to all
)

# 3. Year Range Slider
min_year = int(df['year'].min())
max_year = int(df['year'].max())
selected_years = st.sidebar.slider(
    "Select Year Range",
    min_year, max_year, (min_year, max_year)
)

# 4. Per Capita Toggle
st.sidebar.markdown("---")
has_population = 'population' in df.columns and df['population'].notna().any()
if has_population:
    per_capita_mode = st.sidebar.toggle("Per Capita Mode (per 100k)", value=False)
else:
    per_capita_mode = False
    st.sidebar.info("Population data not available")

# --- FILTERING LOGIC ---
filtered_df = df[
    (df['city'].isin(selected_cities)) &
    (df['Crime Type'].isin(selected_types)) &
    (df['year'] >= selected_years[0]) &
    (df['year'] <= selected_years[1])
].copy()

# --- PER CAPITA CALCULATION ---
value_col = 'count'  # Default to absolute counts
value_label = 'Number of Incidents'

if per_capita_mode and has_population:
    # Calculate per 100k population
    filtered_df['per_capita'] = (filtered_df['count'] / filtered_df['population']) * 100000
    value_col = 'per_capita'
    value_label = 'Incidents per 100k'

# --- KEY METRICS ROW ---
# Calculate metrics based on the filtered data
total_incidents = filtered_df['count'].sum()
if per_capita_mode and has_population:
    # For per capita, show average rate across all rows
    avg_value = filtered_df[value_col].mean()
    avg_label = "Avg Rate per 100k"
else:
    avg_value = filtered_df['count'].mean()
    avg_label = "Average per Year"

if len(selected_cities) > 0 and not filtered_df.empty:
    if per_capita_mode and has_population:
        # For per capita, find city with highest average rate
        top_city = filtered_df.groupby('city')[value_col].mean().idxmax()
    else:
        top_city = filtered_df.groupby('city')['count'].sum().idxmax()
else:
    top_city = "N/A"

col1, col2, col3 = st.columns(3)
col1.metric("Total Incidents (Selection)", f"{total_incidents:,.0f}")
col2.metric(avg_label, f"{avg_value:,.1f}")
col3.metric("Highest Crime City (Selection)", top_city)

st.markdown("###") # Spacer

# --- MAIN CHARTS ---

tab1, tab2, tab3 = st.tabs(["📈 Time Series Trend", "📊 City Comparison", "📅 Heatmap"])

with tab1:
    st.subheader("Crime Trends Over Time")
    
    # Aggregating data for the line chart
    if per_capita_mode and has_population:
        # For per capita, we need to sum counts and population separately, then calculate rate
        line_df = filtered_df.groupby(['city', 'year']).agg({'count': 'sum', 'population': 'first'}).reset_index()
        line_df['per_capita'] = (line_df['count'] / line_df['population']) * 100000
        y_col = 'per_capita'
        chart_title = f"Crime Rate per 100k over Time by City ({selected_years[0]}-{selected_years[1]})"
    else:
        line_df = filtered_df.groupby(['city', 'year'])['count'].sum().reset_index()
        y_col = 'count'
        chart_title = f"Total Incidents over Time by City ({selected_years[0]}-{selected_years[1]})"
    
    if not line_df.empty:
        fig_line = px.line(
            line_df, 
            x='year', 
            y=y_col, 
            color='city', 
            markers=True,
            title=chart_title,
            labels={y_col: value_label, 'year': 'Year', 'city': 'City'}
        )
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, width="stretch")
    else:
        st.info("No data available for the current selection.")

with tab2:
    st.subheader("Crime Composition by City")
    
    # Bar chart showing the breakdown of crime types per city
    if per_capita_mode and has_population:
        bar_df = filtered_df.groupby(['city', 'Crime Type']).agg({'count': 'sum', 'population': 'first'}).reset_index()
        bar_df['per_capita'] = (bar_df['count'] / bar_df['population']) * 100000
        y_col = 'per_capita'
        bar_title = "Crime Rate per 100k by Type and City"
    else:
        bar_df = filtered_df.groupby(['city', 'Crime Type'])['count'].sum().reset_index()
        y_col = 'count'
        bar_title = "Total Incidents by Type and City"
    
    if not bar_df.empty:
        fig_bar = px.bar(
            bar_df, 
            x='city', 
            y=y_col, 
            color='Crime Type', 
            title=bar_title,
            labels={y_col: value_label, 'city': 'City'},
            barmode='stack'
        )
        st.plotly_chart(fig_bar, width="stretch")
    else:
        st.info("No data available for the current selection.")

with tab3:
    st.subheader("Yearly Intensity Heatmap")
    
    if not filtered_df.empty:
        # 1. Aggregate data
        if per_capita_mode and has_population:
            heatmap_data = filtered_df.groupby(['city', 'year']).agg({'count': 'sum', 'population': 'first'}).reset_index()
            heatmap_data['per_capita'] = (heatmap_data['count'] / heatmap_data['population']) * 100000
            heat_value_col = 'per_capita'
            heat_color_label = 'Rate per 100k'
            heat_title = "Heatmap of Crime Rate per 100k"
        else:
            heatmap_data = filtered_df.groupby(['city', 'year'])['count'].sum().reset_index()
            heat_value_col = 'count'
            heat_color_label = 'Incidents'
            heat_title = "Heatmap of Crime Intensity"
        
        # 2. Pivot to create a matrix (Rows=City, Cols=Year)
        # This automatically puts NaN where there is no data for a specific combination
        heatmap_matrix = heatmap_data.pivot(index='city', columns='year', values=heat_value_col)
        
        # 3. Ensure ALL selected years are columns (even if empty)
        full_year_range = list(range(selected_years[0], selected_years[1] + 1))
        
        # Reindex to ensure the grid is complete based on user selection
        heatmap_matrix = heatmap_matrix.reindex(index=selected_cities, columns=full_year_range)
        
        # 4. Create Heatmap using imshow
        fig_heat = px.imshow(
            heatmap_matrix,
            labels=dict(x="Year", y="City", color=heat_color_label),
            x=heatmap_matrix.columns,
            y=heatmap_matrix.index,
            color_continuous_scale='RdYlGn_r', # Green (Low) -> Red (High)
            text_auto='.0f' if not per_capita_mode else '.1f', 
            aspect="auto"
        )

        # 5. Styling: Set plot background to black so NaNs appear black
        fig_heat.update_layout(
            plot_bgcolor='black', 
            xaxis=dict(dtick=1, side='bottom'),
            title=heat_title
        )
        
        st.plotly_chart(fig_heat, width="stretch")
    else:
        st.info("No data available for the current selection.")

# --- RAW DATA VIEW ---
with st.expander("📂 View Raw Data"):
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values(by=['city', 'year', 'Crime Type']), width="stretch")