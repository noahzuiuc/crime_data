import os
from dotenv import load_dotenv
from openai import OpenAI
import csv
import base64
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import io

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


def find_page_with_text(pdf_path: Path, search_text: str) -> list[int]:
    """Find the page numbers containing the specified text."""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if search_text.lower() in text.lower():
            pages.append(i)
    if not pages:
        raise ValueError(f"Text '{search_text}' not found in PDF {pdf_path}")
    return pages


def remove_images_from_pdf(pdf_path: Path, page_num: int) -> bytes:
    """Remove images from a specific page of PDF and return compressed PDF as bytes."""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    page = reader.pages[page_num]
    # Remove images by clearing the XObject resources
    if '/Resources' in page:
        if '/XObject' in page['/Resources']:
            xobjects = page['/Resources']['/XObject'].get_object()
            # Remove all image XObjects
            keys_to_remove = []
            for key in xobjects:
                obj = xobjects[key]
                if hasattr(obj, '/Subtype') and obj['/Subtype'] == '/Image':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del xobjects[key]
    
    writer.add_page(page)
    
    # Compress and write to bytes
    output = io.BytesIO()
    writer.write(output)
    writer.compress_identical_objects()
    
    return output.getvalue()


def combine_pages_to_pdf(pdf_path: Path, page_nums: list[int]) -> bytes:
    """Combine specified pages into a new PDF and return as bytes."""
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    for page_num in page_nums:
        writer.add_page(reader.pages[page_num])
    
    output = io.BytesIO()
    writer.write(output)
    writer.compress_identical_objects()
    
    return output.getvalue()


def encode_pdf_to_base64(pdf_bytes: bytes) -> str:
    """Encode PDF bytes to base64 string."""
    return base64.b64encode(pdf_bytes).decode('utf-8')


def extract_year_from_filename(filename: str) -> str:
    """Extract year from filename (e.g., '2014-Annual-Report.pdf' -> '2014')."""
    return Path(filename).stem.split("-")[0]


def query_openai_for_category(pdf_base64: str, category: str, year: str, filename: str) -> str:
    """Query OpenAI to extract crime count for a specific category and year."""
    
    data_url = f"data:application/pdf;base64,{pdf_base64}"
    
    completion = client.chat.completions.create(
        model="google/gemini-3-pro-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""How many {category} crimes were committed in {year} according to the PDF? Please provide only the number. You may include crimes that are synonyms i.e.\
                        homicide may be called criminal homicide (murder) or murder.\
                        larceny may be called theft or larceny theft.\
                        grand theft auto may be called motor vehicle theft.\
                        sexual assault may be called rape or criminal sexual assault (rape) or criminal sexual assault."""
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
    input_folder = script_dir.parent / "Chicago, Illinois" / "input"
    output_folder = script_dir.parent / "Chicago, Illinois" / "output"
    
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
        
        try:
            page_nums = find_page_with_text(pdf_path, "Index Crime")
            print(f"  Found 'Index Crime' on pages {[p + 1 for p in page_nums]}")
        except ValueError as e:
            print(f"  Error: {e}")
            continue
        
        # Combine the found pages into a new PDF
        pdf_bytes = combine_pages_to_pdf(pdf_path, page_nums)
        pdf_base64 = encode_pdf_to_base64(pdf_bytes)
        
        # Query for each crime category using the combined PDF
        for category in CRIME_CATEGORIES:
            print(f"  Querying for {category}...")
            try:
                count = query_openai_for_category(pdf_base64, category, year, pdf_path.name)
                category_data[category].append((year, count))
                print(f"    Result: {count}")
            except Exception as e:
                print(f"    Error: {e}")
                category_data[category].append((year, "ERROR"))
        
        # Write CSV files for each category after processing this year
        print(f"\n  Writing CSV files for {year}...")
        for category in CRIME_CATEGORIES:
            write_category_csv(category, category_data[category], output_folder)
    
    print(f"\nDone! All files saved to: {output_folder}")
