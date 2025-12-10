import os
from dotenv import load_dotenv
from openai import OpenAI
import csv
import base64
from pathlib import Path
import pandas as pd

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


def load_dc_population_data():
    """
    Load Washington DC population data from Excel files.
    
    Returns:
        dict: Dictionary with year (int) as key and population (int) as value
    """
    script_dir = Path(__file__).parent
    dc_folder = script_dir.parent / "Washington, DC"
    
    population = {}
    
    # Load 2010-2020 data
    file_2010_2020 = dc_folder / "dc_city_population_2010_2020.xlsx"
    if file_2010_2020.exists():
        df = pd.read_excel(file_2010_2020, header=None)
        # Washington DC is at row 4
        row = df.iloc[4]
        # Columns: 0=City, 1=April 2010 Base, 2=2010, 3=2011, ... 11=2019, 12=April 2020 Census
        for year_offset, col_idx in enumerate(range(2, 12)):  # cols 2-11 for 2010-2019
            year = 2010 + year_offset
            pop = row[col_idx]
            if pd.notna(pop):
                population[year] = int(pop)
    
    # Load 2020-2024 data  
    file_2020_2024 = dc_folder / "dc_city_population_2020_2024.xlsx"
    if file_2020_2024.exists():
        df = pd.read_excel(file_2020_2024, header=None)
        # Washington DC is at row 4
        row = df.iloc[4]
        # Columns: 0=City, 1=April 2020 Base, 2=2020, 3=2021, 4=2022, 5=2023, 6=2024
        for year_offset, col_idx in enumerate(range(2, 7)):  # cols 2-6 for 2020-2024
            year = 2020 + year_offset
            pop = row[col_idx]
            if pd.notna(pop):
                population[year] = int(pop)
    
    return population


def load_crime_categories() -> list:
    """Load crime categories from crime_categories.txt file."""
    script_dir = Path(__file__).parent
    categories_file = script_dir / "crime_categories.txt"
    
    with open(categories_file, "r", encoding="utf-8") as f:
        categories = [line.strip() for line in f if line.strip()]
    
    return categories


# Crime categories to extract
CRIME_CATEGORIES = load_crime_categories()


def encode_pdf_to_base64(pdf_path: Path) -> str:
    """Encode a PDF file to base64 string."""
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')


def extract_year_from_filename(filename: str) -> str:
    """Extract year from filename (e.g., '2014.pdf' -> '2014')."""
    return Path(filename).stem


def query_openai_for_category(pdf_base64: str, category: str, year: str, filename: str) -> str:
    """Query OpenAI to extract crime count for a specific category and year."""
    
    data_url = f"data:application/pdf;base64,{pdf_base64}"
    
    completion = client.chat.completions.create(
        model="google/gemini-3-pro-exp",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"How many {category} crimes were committed in {year} according to the PDF? Please provide only the number."
                    },
                    {
                        "type": "file",
                        "file": {
                            "filename": filename,
                            "file_data": data_url
                        }
                    }
                ],
            }
        ],
        extra_body={
            "plugins": [
                {
                    "id": "file-parser",
                    "pdf": {
                        "engine": "pdf-text"
                    }
                }
            ]
        }
    )
    
    response = completion.choices[0].message.content
    return str(response).strip().replace(',', '')


def write_category_csv(category: str, data: list, output_folder: Path, population_data: dict = None):
    """Write crime data for a category to CSV file."""
    output_folder.mkdir(parents=True, exist_ok=True)
    csv_path = output_folder / f"{category}.csv"
    
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if population_data:
            writer.writerow(["year", "count", "population"])
            for year, count in sorted(data):
                pop = population_data.get(int(year), "")
                writer.writerow([year, count, pop])
        else:
            writer.writerow(["year", "count"])
            for year, count in sorted(data):
                writer.writerow([year, count])
    
    print(f"  Wrote: {csv_path.name}")


def update_existing_csvs_with_population():
    """
    Update existing Washington DC output CSVs to add population column.
    Useful when CSVs were already generated without population data.
    """
    population = load_dc_population_data()
    output_folder = Path(__file__).parent.parent / "Washington, DC" / "output"
    
    if not output_folder.exists():
        print(f"Output folder not found: {output_folder}")
        return
    
    for csv_file in output_folder.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            if 'year' in df.columns and 'population' not in df.columns:
                df['population'] = df['year'].map(population)
                df.to_csv(csv_file, index=False)
                print(f"Updated: {csv_file.name}")
            elif 'population' in df.columns:
                print(f"Skipped (already has population): {csv_file.name}")
        except Exception as e:
            print(f"Error updating {csv_file.name}: {e}")


if __name__ == "__main__":
    import sys
    
    # If --update-population flag is passed, just update existing CSVs
    if len(sys.argv) > 1 and sys.argv[1] == "--update-population":
        print("Updating existing CSVs with population data...")
        update_existing_csvs_with_population()
        sys.exit(0)
    
    # Load population data
    population_data = load_dc_population_data()
    print(f"Loaded DC population data for years: {sorted(population_data.keys())}")
    
    # Get paths
    script_dir = Path(__file__).parent
    input_folder = script_dir.parent / "Washington, DC" / "input"
    output_folder = script_dir.parent / "Washington, DC" / "output"
    
    # Get all PDF files
    pdf_files = sorted(input_folder.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        exit(1)
    
    print(f"Found {len(pdf_files)} PDF files")
    
    # Dictionary to store data for each category
    category_data = {category: [] for category in CRIME_CATEGORIES}
    
    # Process each PDF file
    for pdf_path in pdf_files:
        year = extract_year_from_filename(pdf_path.name)
        print(f"\nProcessing {pdf_path.name} (Year: {year})...")
        
        # Encode PDF to base64
        pdf_base64 = encode_pdf_to_base64(pdf_path)
        
        # Dictionary to store data for this year
        year_data = {}
        
        # Query for each crime category
        for category in CRIME_CATEGORIES:
            print(f"  Querying for {category}...")
            try:
                count = query_openai_for_category(pdf_base64, category, year, pdf_path.name)
                year_data[category] = count
                category_data[category].append((year, count))
                print(f"    Result: {count}")
            except Exception as e:
                print(f"    Error: {e}")
                year_data[category] = "ERROR"
                category_data[category].append((year, "ERROR"))
        
        # Write CSV files for each category after processing this year
        print(f"\n  Writing CSV files for {year}...")
        for category in CRIME_CATEGORIES:
            write_category_csv(category, category_data[category], output_folder, population_data)
    
    print(f"\nDone! All files saved to: {output_folder}")
