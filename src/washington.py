import os
from dotenv import load_dotenv
from openai import OpenAI
import csv
import base64
from pathlib import Path

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


def load_crime_categories() -> list:
    """Load crime categories from crime_catagories.txt file."""
    script_dir = Path(__file__).parent
    categories_file = script_dir / "crime_catagories.txt"
    
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
        model="google/gemini-2.5-flash-lite",
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


def write_category_csv(category: str, data: list, output_folder: Path):
    """Write crime data for a category to CSV file."""
    output_folder.mkdir(parents=True, exist_ok=True)
    csv_path = output_folder / f"{category}.csv"
    
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "count"])
        for year, count in sorted(data):
            writer.writerow([year, count])
    
    print(f"  Wrote: {csv_path.name}")


if __name__ == "__main__":
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
            write_category_csv(category, category_data[category], output_folder)
    
    print(f"\nDone! All files saved to: {output_folder}")
