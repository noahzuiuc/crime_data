import os
import pandas as pd
from pathlib import Path

def combine_crime_data():
    # 1. Setup Paths
    # We are inside 'src', so we go up one level to find the city folders
    base_dir = Path('..').resolve() 
    output_dir = base_dir / "Combined Data"
    
    # Create the Combined Data folder if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Dictionary to hold lists of dataframes, keyed by filename (e.g., 'robbery.csv')
    # Structure: { 'robbery.csv': [df_chicago, df_la], 'arson.csv': [df_la] }
    crime_files_map = {}

    print(f"Scanning directories in {base_dir}...\n")

    # 2. Iterate through all folders in the base directory
    for item in base_dir.iterdir():
        
        # We only care about directories that are NOT 'src' or 'Combined Data'
        if item.is_dir() and item.name not in ['src', 'Combined Data', 'crime_data_env', '.git']:
            
            # Check if this directory has an 'output' folder (this confirms it's a City folder)
            city_output_path = item / 'output'
            
            if city_output_path.exists():
                city_name = item.name # e.g., "Chicago, Illinois"
                print(f"Processing City: {city_name}")

                # 3. Read every CSV in the city's output folder
                csv_files = list(city_output_path.glob('*.csv'))
                
                if not csv_files:
                    print(f"  - No CSVs found in {city_name}")
                    continue

                for csv_file in csv_files:
                    try:
                        # Read the CSV
                        df = pd.read_csv(csv_file)
                        
                        # Add the City column
                        df['city'] = city_name
                        
                        # Add to our map
                        if csv_file.name not in crime_files_map:
                            crime_files_map[csv_file.name] = []
                        
                        crime_files_map[csv_file.name].append(df)
                        
                    except Exception as e:
                        print(f"  - Error reading {csv_file.name}: {e}")

    print("\n------------------------------------------------")
    print("Consolidating files...")

    # 4. Concatenate and Save
    if not crime_files_map:
        print("No crime data found to combine.")
        return

    for filename, dataframe_list in crime_files_map.items():
        # Combine all cities for this specific crime type
        combined_df = pd.concat(dataframe_list, ignore_index=True)
        
        # Organize columns: City, Year, Count (Subjective preference, can be changed)
        # Using the column names from your example: 'year', 'count', 'city'
        cols = ['city', 'year', 'count']
        
        # Ensure columns exist before reordering (just for safety)
        existing_cols = [c for c in cols if c in combined_df.columns]
        combined_df = combined_df[existing_cols]

        # Save to Combined Data folder
        save_path = output_dir / filename
        combined_df.to_csv(save_path, index=False)
        print(f"Saved: {filename} ({len(combined_df)} total rows)")

    print("------------------------------------------------")
    print(f"Done! All combined files are in: {output_dir}")

if __name__ == "__main__":
    combine_crime_data()