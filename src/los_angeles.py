import os
import pandas as pd
from pathlib import Path

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
    
    # Read all CSV files in the input folder
    for csv_file in sorted(input_folder.glob("*.csv")):
        # Extract year from filename (e.g., "2014-PART_I_AND_II_CRIMES.csv" -> "2014")
        year = csv_file.stem.split("-")[0]
        
        # Read CSV into DataFrame with error handling for malformed lines
        df = pd.read_csv(csv_file, on_bad_lines='warn', engine='python')
        
        # Store in dictionary
        crime_data[year] = df
        
        print(f"Loaded {year}: {len(df)} records")
    
    return crime_data


def create_category_csvs(crime_data):
    """
    Create CSV files for each crime category with year and count columns.
    
    Args:
        crime_data: Dictionary with year as key and DataFrame as value
    """
    script_dir = Path(__file__).parent
    output_folder = script_dir.parent / "Los Angeles, California" / "output"
    
    # Create output folder if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Combine all years into one DataFrame with year column
    all_data = []
    for year, df in crime_data.items():
        df_copy = df.copy()
        df_copy['YEAR'] = int(year)
        all_data.append(df_copy)
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Get all unique categories
    categories = combined_df['CATEGORY'].unique()
    categories = [cat for cat in categories if pd.notna(cat)]  # Remove NaN categories
    
    print(f"\nFound {len(categories)} unique categories")
    print(f"Processing categories...")
    
    # For each category, create a CSV with year and count
    for category in sorted(categories):
        # Filter data for this category
        category_data = combined_df[combined_df['CATEGORY'] == category]
        
        # Group by year and count
        yearly_counts = category_data.groupby('YEAR').size().reset_index(name='count')
        
        # Sort by year
        yearly_counts = yearly_counts.sort_values('YEAR')
        
        # Rename YEAR column to lowercase year
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
    data = load_la_crime_data()
    
    # Print summary
    print(f"\nTotal years loaded: {len(data)}")
    print(f"Years: {list(data.keys())}")
    
    # Create CSV files for each category
    create_category_csvs(data)
