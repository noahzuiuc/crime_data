import os
import pandas as pd
from pathlib import Path


def load_portland_population_data():
    # Collect Portland population figures from the census spreadsheets
    script_dir = Path(__file__).parent
    portland_folder = script_dir.parent / "Portland, Oregon"
    
    population = {}
    
    file_2010_2020 = portland_folder / "oregon_city_population_2010_2020.xlsx"
    if file_2010_2020.exists():
        df = pd.read_excel(file_2010_2020, header=None)
        for i, row in df.iterrows():
            if 'Portland city' in str(row[0]):
                for year_offset, col_idx in enumerate(range(2, 12)):
                    year = 2010 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    file_2020_2024 = portland_folder / "oregon_city_population_2020_2024.xlsx"
    if file_2020_2024.exists():
        df = pd.read_excel(file_2020_2024, header=None)
        for i, row in df.iterrows():
            if 'Portland city' in str(row[0]):
                for year_offset, col_idx in enumerate(range(2, 7)):
                    year = 2020 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    return population


def load_portland_crime_data():
    # Load the annual Portland crime CSVs and return a year-indexed mapping
    script_dir = Path(__file__).parent
    input_folder = script_dir.parent / "Portland, Oregon" / "input"
    
    crime_data = {}
    
    if not input_folder.exists():
        print(f"Error: Input folder not found at {input_folder}")
        return {}
    
    for csv_file in sorted(input_folder.glob("*.csv")):
        try:
            year = csv_file.stem.split("_")[-1]
            
            df = pd.read_csv(csv_file, on_bad_lines='warn', engine='python')
            
            crime_data[year] = df
            
            print(f"Loaded {year}: {len(df)} records")
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
    
    return crime_data


def create_category_csvs(crime_data, population_data=None):
    # Assemble per-category crime trends and write them to CSV, merging population if provided
    if not crime_data:
        print("No data available to process.")
        return

    script_dir = Path(__file__).parent
    output_folder = script_dir.parent / "Portland, Oregon" / "output"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    all_data = []
    for year, df in crime_data.items():
        df_copy = df.copy()
        df_copy['YEAR'] = int(year)
        all_data.append(df_copy)
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    target_column = 'CustomCrimeCategory'
    
    if target_column not in combined_df.columns:
        if 'OffenseType' in combined_df.columns:
            print(f"Generating '{target_column}' from 'OffenseType'...")
            
            mapping = {
                'Motor Vehicle Theft': 'Vehicle Crime',
                'Theft From Motor Vehicle': 'Vehicle Crime',
                'Burglary': 'Property Crime',
                'Vandalism': 'Property Crime',
                'Aggravated Assault': 'Violent Crime',
            }
            
            def map_category(offense):
                return mapping.get(offense, offense)

            combined_df[target_column] = combined_df['OffenseType'].apply(map_category)
        else:
            print(f"Error: Could not generate {target_column} because 'OffenseType' is missing.")
            return

    categories = combined_df[target_column].unique()
    categories = [cat for cat in categories if pd.notna(cat)]
    
    print(f"\nFound {len(categories)} unique custom categories")
    print(f"Processing categories...")
    
    for category in sorted(categories):
        category_data = combined_df[combined_df[target_column] == category]
        
        yearly_counts = category_data.groupby('YEAR').size().reset_index(name='count')
        yearly_counts = yearly_counts.sort_values('YEAR')
        yearly_counts = yearly_counts.rename(columns={'YEAR': 'year'})
        
        if population_data:
            yearly_counts['population'] = yearly_counts['year'].map(population_data)
        
        safe_filename = category.lower().replace(' ', '-').replace('/', '-').replace('&', 'and')
        safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in ['-', '_'])
        
        output_path = output_folder / f"{safe_filename}.csv"
        
        yearly_counts.to_csv(output_path, index=False)
        print(f"  Created: {safe_filename}.csv ({len(yearly_counts)} years)")
    
    print(f"\nAll category CSV files saved to: {output_folder}")


if __name__ == "__main__":
    data = load_portland_crime_data()
    
    population = load_portland_population_data()
    print(f"Loaded population data for years: {sorted(population.keys())}")
    
    print(f"\nTotal years loaded: {len(data)}")
    if data:
        create_category_csvs(data, population)