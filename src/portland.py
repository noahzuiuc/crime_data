import os
import pandas as pd
from pathlib import Path


def load_portland_population_data():
    """
    Load Portland city population data from Excel files.
    
    Returns:
        dict: Dictionary with year (int) as key and population (int) as value
    """
    script_dir = Path(__file__).parent
    portland_folder = script_dir.parent / "Portland, Oregon"
    
    population = {}
    
    # Load 2010-2020 data
    file_2010_2020 = portland_folder / "oregon_city_population_2010_2020.xlsx"
    if file_2010_2020.exists():
        df = pd.read_excel(file_2010_2020, header=None)
        # Find Portland row
        for i, row in df.iterrows():
            if 'Portland city' in str(row[0]):
                # Columns: 0=City, 1=April 2010 Base, 2=2010, 3=2011, ... 11=2019, 12=April 2020 Census
                for year_offset, col_idx in enumerate(range(2, 12)):  # cols 2-11 for 2010-2019
                    year = 2010 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    # Load 2020-2024 data  
    file_2020_2024 = portland_folder / "oregon_city_population_2020_2024.xlsx"
    if file_2020_2024.exists():
        df = pd.read_excel(file_2020_2024, header=None)
        # Find Portland row
        for i, row in df.iterrows():
            if 'Portland city' in str(row[0]):
                # Columns: 0=City, 1=April 2020 Base, 2=2020, 3=2021, 4=2022, 5=2023, 6=2024
                for year_offset, col_idx in enumerate(range(2, 7)):  # cols 2-6 for 2020-2024
                    year = 2020 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    return population


def load_portland_crime_data():
    """
    Load all Portland crime CSV files from the input folder into a dictionary.
    
    Returns:
        dict: Dictionary with year as key and DataFrame as value
    """
    # Get the path to the Portland input folder
    script_dir = Path(__file__).parent
    input_folder = script_dir.parent / "Portland, Oregon" / "input"
    
    # Dictionary to store DataFrames
    crime_data = {}
    
    # Check if input directory exists
    if not input_folder.exists():
        print(f"Error: Input folder not found at {input_folder}")
        return {}
    
    # Read all CSV files in the input folder
    for csv_file in sorted(input_folder.glob("*.csv")):
        try:
            year = csv_file.stem.split("_")[-1]
            
            # Read CSV into DataFrame
            df = pd.read_csv(csv_file, on_bad_lines='warn', engine='python')
            
            # Store in dictionary
            crime_data[year] = df
            
            print(f"Loaded {year}: {len(df)} records")
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
    
    return crime_data


def create_category_csvs(crime_data, population_data=None):
    """
    Create CSV files for each CustomCrimeCategory with year, count, and population columns.
    """
    if not crime_data:
        print("No data available to process.")
        return

    script_dir = Path(__file__).parent
    output_folder = script_dir.parent / "Portland, Oregon" / "output"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Combine all years into one DataFrame
    all_data = []
    for year, df in crime_data.items():
        df_copy = df.copy()
        df_copy['YEAR'] = int(year)
        all_data.append(df_copy)
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # --- STEP 1: DEFINE TARGET COLUMN ---
    target_column = 'CustomCrimeCategory'
    
    # --- STEP 2: CREATE MAPPING LOGIC ---
    # If the column doesn't exist in source data, we must create it from OffenseType
    if target_column not in combined_df.columns:
        if 'OffenseType' in combined_df.columns:
            print(f"Generating '{target_column}' from 'OffenseType'...")
            
            # ---------------------------------------------------------
            # TODO: EDIT THIS DICTIONARY TO DEFINE YOUR CUSTOM GROUPS
            # ---------------------------------------------------------
            mapping = {
                # Example Mappings:
                'Motor Vehicle Theft': 'Vehicle Crime',
                'Theft From Motor Vehicle': 'Vehicle Crime',
                'Burglary': 'Property Crime',
                'Vandalism': 'Property Crime',
                'Aggravated Assault': 'Violent Crime',
                # Add your specific mappings here
            }
            
            # Function to apply mapping
            def map_category(offense):
                # Return the mapped value, or the original name if not found in dict
                return mapping.get(offense, offense)

            # Create the new column
            combined_df[target_column] = combined_df['OffenseType'].apply(map_category)
        else:
            print(f"Error: Could not generate {target_column} because 'OffenseType' is missing.")
            return

    # Get all unique types from the NEW column
    categories = combined_df[target_column].unique()
    categories = [cat for cat in categories if pd.notna(cat)]
    
    print(f"\nFound {len(categories)} unique custom categories")
    print(f"Processing categories...")
    
    # For each category, create a CSV with year and count
    for category in sorted(categories):
        # Filter data for this specific CustomCrimeCategory
        category_data = combined_df[combined_df[target_column] == category]
        
        # Group by YEAR and count
        yearly_counts = category_data.groupby('YEAR').size().reset_index(name='count')
        yearly_counts = yearly_counts.sort_values('YEAR')
        yearly_counts = yearly_counts.rename(columns={'YEAR': 'year'})
        
        # Add population column if population data is available
        if population_data:
            yearly_counts['population'] = yearly_counts['year'].map(population_data)
        
        # Create filename
        safe_filename = category.lower().replace(' ', '-').replace('/', '-').replace('&', 'and')
        safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in ['-', '_'])
        
        output_path = output_folder / f"{safe_filename}.csv"
        
        yearly_counts.to_csv(output_path, index=False)
        print(f"  Created: {safe_filename}.csv ({len(yearly_counts)} years)")
    
    print(f"\nAll category CSV files saved to: {output_folder}")


if __name__ == "__main__":
    # Load the data
    data = load_portland_crime_data()
    
    # Load population data
    population = load_portland_population_data()
    print(f"Loaded population data for years: {sorted(population.keys())}")
    
    # Print summary
    print(f"\nTotal years loaded: {len(data)}")
    if data:
        # Create CSV files using CustomCrimeCategory
        create_category_csvs(data, population)