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

# --- FILTERING LOGIC ---
filtered_df = df[
    (df['city'].isin(selected_cities)) &
    (df['Crime Type'].isin(selected_types)) &
    (df['year'] >= selected_years[0]) &
    (df['year'] <= selected_years[1])
]

# --- KEY METRICS ROW ---
# Calculate metrics based on the filtered data
total_incidents = filtered_df['count'].sum()
avg_incidents = filtered_df['count'].mean()
if len(selected_cities) > 0 and not filtered_df.empty:
    top_city = filtered_df.groupby('city')['count'].sum().idxmax()
else:
    top_city = "N/A"

col1, col2, col3 = st.columns(3)
col1.metric("Total Incidents (Selection)", f"{total_incidents:,.0f}")
col2.metric("Average per Year", f"{avg_incidents:,.0f}")
col3.metric("Highest Crime City (Selection)", top_city)

st.markdown("###") # Spacer

# --- MAIN CHARTS ---

tab1, tab2, tab3 = st.tabs(["📈 Time Series Trend", "📊 City Comparison", "📅 Heatmap"])

with tab1:
    st.subheader("Crime Trends Over Time")
    
    # Aggregating data for the line chart
    line_df = filtered_df.groupby(['city', 'year'])['count'].sum().reset_index()
    
    if not line_df.empty:
        fig_line = px.line(
            line_df, 
            x='year', 
            y='count', 
            color='city', 
            markers=True,
            title=f"Total Incidents over Time by City ({selected_years[0]}-{selected_years[1]})",
            labels={'count': 'Number of Incidents', 'year': 'Year', 'city': 'City'}
        )
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, width="stretch")
    else:
        st.info("No data available for the current selection.")

with tab2:
    st.subheader("Crime Composition by City")
    
    # Bar chart showing the breakdown of crime types per city
    bar_df = filtered_df.groupby(['city', 'Crime Type'])['count'].sum().reset_index()
    
    if not bar_df.empty:
        fig_bar = px.bar(
            bar_df, 
            x='city', 
            y='count', 
            color='Crime Type', 
            title="Total Incidents by Type and City",
            labels={'count': 'Total Incidents', 'city': 'City'},
            barmode='stack'
        )
        st.plotly_chart(fig_bar, width="stretch")
    else:
        st.info("No data available for the current selection.")

with tab3:
    st.subheader("Yearly Intensity Heatmap")
    
    if not filtered_df.empty:
        # 1. Aggregate data
        heatmap_data = filtered_df.groupby(['city', 'year'])['count'].sum().reset_index()
        
        # 2. Pivot to create a matrix (Rows=City, Cols=Year)
        # This automatically puts NaN where there is no data for a specific combination
        heatmap_matrix = heatmap_data.pivot(index='city', columns='year', values='count')
        
        # 3. Ensure ALL selected years are columns (even if empty)
        full_year_range = list(range(selected_years[0], selected_years[1] + 1))
        
        # Reindex to ensure the grid is complete based on user selection
        heatmap_matrix = heatmap_matrix.reindex(index=selected_cities, columns=full_year_range)
        
        # 4. Create Heatmap using imshow
        fig_heat = px.imshow(
            heatmap_matrix,
            labels=dict(x="Year", y="City", color="Incidents"),
            x=heatmap_matrix.columns,
            y=heatmap_matrix.index,
            color_continuous_scale='RdYlGn_r', # Green (Low) -> Red (High)
            text_auto=True, 
            aspect="auto"
        )

        # 5. Styling: Set plot background to black so NaNs appear black
        fig_heat.update_layout(
            plot_bgcolor='black', 
            xaxis=dict(dtick=1, side='bottom'),
            title="Heatmap of Crime Intensity"
        )
        
        st.plotly_chart(fig_heat, width="stretch")
    else:
        st.info("No data available for the current selection.")

# --- RAW DATA VIEW ---
with st.expander("📂 View Raw Data"):
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values(by=['city', 'year', 'Crime Type']), width="stretch")