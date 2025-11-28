import os
import pandas as pd
from pathlib import Path

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


def create_category_csvs(crime_data):
    """
    Create CSV files for each CustomCrimeCategory with year and count columns.
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
    
    # Print summary
    print(f"\nTotal years loaded: {len(data)}")
    if data:
        # Create CSV files using CustomCrimeCategory
        create_category_csvs(data)