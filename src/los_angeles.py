import os
import pandas as pd
from pathlib import Path

def load_la_population_data():
    """
    Load Los Angeles County population data from Excel files.
    
    Returns:
        dict: Dictionary with year (int) as key and population (int) as value
    """
    script_dir = Path(__file__).parent
    la_folder = script_dir.parent / "Los Angeles, California"
    
    population = {}
    
    # Load 2010-2020 data
    file_2010_2020 = la_folder / "california_county_population_2010_2020.xlsx"
    if file_2010_2020.exists():
        df = pd.read_excel(file_2010_2020, header=None)
        # Find Los Angeles row
        for i, row in df.iterrows():
            if 'Los Angeles' in str(row[0]):
                # Columns: 0=County, 1=April 2010, 2=Estimates Base, 
                # 3-12 = 2010-2019 estimates, 13=April 2020 Census
                # Based on row 3, col 2=2010, col 3=2011, ... col 11=2019
                for year_offset, col_idx in enumerate(range(2, 12)):  # cols 2-11 for 2010-2019
                    year = 2010 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    # Load 2020-2024 data  
    file_2020_2024 = la_folder / "california_county_population_2020_2024.xlsx"
    if file_2020_2024.exists():
        df = pd.read_excel(file_2020_2024, header=None)
        # Find Los Angeles row
        for i, row in df.iterrows():
            if 'Los Angeles' in str(row[0]):
                # Columns: 0=County, 1=April 2020 Base, 2=2020, 3=2021, 4=2022, 5=2023, 6=2024
                for year_offset, col_idx in enumerate(range(2, 7)):  # cols 2-6 for 2020-2024
                    year = 2020 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    return population


def load_la_crime_data():
    """
    Load all Los Angeles crime CSV files from the input folder into a dictionary.
    
    Returns:
        dict: Dictionary with year as key and DataFrame as value
    """
    # Get the path to the Los Angeles input folder
    script_dir = Path(__file__).parent
    input_folder = script_dir.parent / "Los Angeles, California" / "input"
    
    # Dictionary to store DataFrames
    crime_data = {}
    
    # Check if input directory exists
    if not input_folder.exists():
        print(f"Error: Input folder not found at {input_folder}")
        return {}
    
    # Read all CSV files in the input folder
    for csv_file in sorted(input_folder.glob("*.csv")):
        # Extract year from filename (e.g., "2014-PART_I_AND_II_CRIMES.csv" -> "2014")
        year = csv_file.stem.split("-")[0]
        
        # Read CSV into DataFrame with error handling for malformed lines
        try:
            df = pd.read_csv(csv_file, on_bad_lines='warn', engine='python')
            
            # Store in dictionary
            crime_data[year] = df
            
            print(f"Loaded {year}: {len(df)} records")
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
    
    return crime_data


def create_category_csvs(crime_data, population_data=None):
    """
    Create CSV files for each crime category with year, count, and population columns.
    
    Args:
        crime_data: Dictionary with year as key and DataFrame as value
        population_data: Dictionary with year (int) as key and population (int) as value
    """
    if not crime_data:
        print("No data available to process.")
        return

    script_dir = Path(__file__).parent
    output_folder = script_dir.parent / "Los Angeles, California" / "output"
    
    # Create output folder if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Combine all years into one DataFrame with year column
    all_data = []
    for year, df in crime_data.items():
        df_copy = df.copy()
        # Create a temporary uppercase YEAR column for grouping
        df_copy['YEAR'] = int(year)
        all_data.append(df_copy)
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Get all unique categories
    if 'CATEGORY' not in combined_df.columns:
        print("Error: 'CATEGORY' column not found in data.")
        return

    categories = combined_df['CATEGORY'].unique()
    categories = [cat for cat in categories if pd.notna(cat)]  # Remove NaN categories
    
    print(f"\nFound {len(categories)} unique categories")
    print(f"Processing categories...")
    
    # For each category, create a CSV with year and count
    for category in sorted(categories):
        # Filter data for this category
        category_data = combined_df[combined_df['CATEGORY'] == category]
        
        # Group by YEAR and count
        yearly_counts = category_data.groupby('YEAR').size().reset_index(name='count')
        
        # Sort by YEAR
        yearly_counts = yearly_counts.sort_values('YEAR')
        
        # --- CRITICAL STEP: Rename 'YEAR' to lowercase 'year' ---
        yearly_counts = yearly_counts.rename(columns={'YEAR': 'year'})
        
        # Add population column if population data is available
        if population_data:
            yearly_counts['population'] = yearly_counts['year'].map(population_data)
        
        # Create filename (sanitize category name for filesystem)
        safe_filename = category.lower().replace(' ', '-').replace('/', '-').replace('&', 'and')
        safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in ['-', '_'])
        output_path = output_folder / f"{safe_filename}.csv"
        
        # Save to CSV
        yearly_counts.to_csv(output_path, index=False)
        
        print(f"  Created: {safe_filename}.csv ({len(yearly_counts)} years)")
    
    print(f"\nAll category CSV files saved to: {output_folder}")


if __name__ == "__main__":
    # Load the data
    data = load_la_crime_data()
    
    # Load population data
    population = load_la_population_data()
    print(f"Loaded population data for years: {sorted(population.keys())}")
    
    # Print summary
    print(f"\nTotal years loaded: {len(data)}")
    if data:
        print(f"Years: {list(data.keys())}")
        
        # Create CSV files for each category
        create_category_csvs(data, population)