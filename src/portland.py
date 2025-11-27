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
        # Extract year from filename (e.g., "New_Offense_Data_2015.csv" -> "2015")
        # Assumes format ends in _YYYY
        try:
            year = csv_file.stem.split("_")[-1]
            
            # Read CSV into DataFrame with error handling for malformed lines
            df = pd.read_csv(csv_file, on_bad_lines='warn', engine='python')
            
            # Store in dictionary
            crime_data[year] = df
            
            print(f"Loaded {year}: {len(df)} records")
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
    
    return crime_data


def create_category_csvs(crime_data):
    """
    Create CSV files for each crime category with year and count columns.
    
    Args:
        crime_data: Dictionary with year as key and DataFrame as value
    """
    if not crime_data:
        print("No data available to process.")
        return

    script_dir = Path(__file__).parent
    output_folder = script_dir.parent / "Portland, Oregon" / "output"
    
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
    
    # Get all unique categories (using Portland's specific column name)
    if 'OffenseCategory' not in combined_df.columns:
        print("Error: 'OffenseCategory' column not found in data.")
        return

    categories = combined_df['OffenseCategory'].unique()
    categories = [cat for cat in categories if pd.notna(cat)]  # Remove NaN categories
    
    print(f"\nFound {len(categories)} unique categories")
    print(f"Processing categories...")
    
    # For each category, create a CSV with year and count
    for category in sorted(categories):
        # Filter data for this category
        category_data = combined_df[combined_df['OffenseCategory'] == category]
        
        # Group by YEAR and count
        yearly_counts = category_data.groupby('YEAR').size().reset_index(name='count')
        
        # Sort by YEAR
        yearly_counts = yearly_counts.sort_values('YEAR')
        
        # --- CRITICAL STEP: Rename 'YEAR' to lowercase 'year' ---
        yearly_counts = yearly_counts.rename(columns={'YEAR': 'year'})
        
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
    data = load_portland_crime_data()
    
    # Print summary
    print(f"\nTotal years loaded: {len(data)}")
    if data:
        print(f"Years: {list(data.keys())}")
        
        # Create CSV files for each category
        create_category_csvs(data)