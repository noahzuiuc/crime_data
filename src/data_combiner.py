import os
from dotenv import load_dotenv
import json
import pandas as pd
from pathlib import Path
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY not found. Create a .env file with OPENROUTER_API_KEY=... or set the environment variable."
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

def load_targets():
    """Load the specific crime categories we care about."""
    txt_path = Path(__file__).parent / "crime_categories.txt"
    if not txt_path.exists():
        print(f"Error: {txt_path} not found.")
        return []
    with open(txt_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_city_mapping(city_name, filenames, targets):
    """
    Sends ALL filenames for a city to the LLM and asks for a JSON mapping
    to the target categories.
    """
    prompt = f"""
    You are a data processing assistant.
    
    I have a list of CSV files containing crime data for the city of {city_name}.
    I have a list of Target Categories I want to map them to.
    
    Target Categories:
    {json.dumps(targets)}
    
    File List:
    {json.dumps(filenames)}
    
    Task:
    Map the files to the Target Categories based on semantic similarity (e.g., "murder" -> "homicide", "motor-vehicle-theft" -> "grand-theft-auto").
    Manslaughter is not homicide.
    
    Rules:
    1. A Target Category can have multiple files mapped to it (e.g. "larceny-shoplifting" and "larceny-from-auto" -> "larceny").
    2. Ignore files that do not match any Target Category.
    3. Return ONLY a valid JSON object where the Keys are the Target Categories and the Values are lists of filenames.
    4. Do not include markdown formatting like ```json.
    
    Example Output Structure:
    {{
      "homicide": ["murder.csv", "manslaughter.csv"],
      "larceny": ["shoplifting.csv"],
      "robbery": []
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="google/gemini-3-pro-preview",
            messages=[
                {"role": "system", "content": "You are a helpful data assistant that outputs raw JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"} 
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Clean up if the model accidentally adds markdown despite instructions
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "")
            
        return json.loads(response_text)

    except Exception as e:
        print(f"    ! API Error mapping {city_name}: {e}")
        return {}

def combine_crime_data():
    targets = load_targets()
    if not targets:
        print("No target categories found in crime_categories.txt")
        return

    base_dir = Path('..').resolve() 
    output_dir = base_dir / "Combined Data"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Global storage: { 'homicide': [df_chicago, df_la], ... }
    aggregated_data = {target: [] for target in targets}

    print(f"Scanning directories in {base_dir}...\n")

    # 1. Iterate through City folders
    for item in base_dir.iterdir():
        if item.is_dir() and item.name not in ['src', 'Combined Data', 'crime_data_env', '.git']:
            
            city_output_path = item / 'output'
            if city_output_path.exists():
                city_name = item.name
                print(f"Processing City: {city_name}")

                # Get all CSVs in this city's folder
                csv_paths = list(city_output_path.glob('*.csv'))
                if not csv_paths:
                    continue
                    
                # Create a map of filename -> full_path for easy loading later
                file_path_map = {p.name: p for p in csv_paths}
                filenames = list(file_path_map.keys())

                # 2. Get the Mapping from LLM
                print(f"  - Querying AI for mapping {len(filenames)} files...")
                mapping = get_city_mapping(city_name, filenames, targets)
                
                # 3. Process the Mapping
                for category, mapped_files in mapping.items():
                    if category not in aggregated_data:
                        continue # Skip categories the LLM hallucinated if any
                        
                    if not mapped_files:
                        continue

                    # Load all files for this specific category (e.g. all 4 larceny files)
                    city_category_dfs = []
                    for fname in mapped_files:
                        if fname in file_path_map:
                            try:
                                df = pd.read_csv(file_path_map[fname])
                                city_category_dfs.append(df)
                            except Exception as e:
                                print(f"    ! Error reading {fname}: {e}")
                    
                    if not city_category_dfs:
                        continue

                    # 4. Merge and Sum (Many-to-One logic)
                    combined_city_df = pd.concat(city_category_dfs, ignore_index=True)
                    
                    # Ensure year is treated consistently
                    if 'year' in combined_city_df.columns and 'count' in combined_city_df.columns:
                        # SUM the counts by year, keep population (same for all rows of a year)
                        agg_dict = {'count': 'sum'}
                        if 'population' in combined_city_df.columns:
                            agg_dict['population'] = 'first'
                        
                        summed_df = combined_city_df.groupby('year').agg(agg_dict).reset_index()
                        
                        # Add metadata
                        summed_df['city'] = city_name
                        
                        # Add to global aggregation
                        aggregated_data[category].append(summed_df)
                        
                        # --- UPDATED LOGGING SECTION ---
                        print(f"  + Mapped {len(mapped_files)} files to '{category}':")
                        for fname in mapped_files:
                            print(f"      - {fname}")
                        # -------------------------------
                        
                    else:
                        print(f"    ! Warning: Missing 'year' or 'count' columns in {category} files for {city_name}")

    print("\n------------------------------------------------")
    print("Consolidating files...")

    # 5. Final Global Concatenation
    for category, dataframe_list in aggregated_data.items():
        if not dataframe_list:
            continue
            
        final_df = pd.concat(dataframe_list, ignore_index=True)
        
        # Organize columns
        cols = ['city', 'year', 'count', 'population']
        existing_cols = [c for c in cols if c in final_df.columns]
        final_df = final_df[existing_cols]

        save_path = output_dir / f"{category}.csv"
        final_df.to_csv(save_path, index=False)
        print(f"Saved: {category}.csv ({len(final_df)} rows)")

    print("------------------------------------------------")
    print(f"Done! Combined files are in: {output_dir}")

if __name__ == "__main__":
    combine_crime_data()