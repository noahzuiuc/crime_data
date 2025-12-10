import os
from dotenv import load_dotenv
from openai import OpenAI
import re
import csv
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

photo_links = ["https://i.ibb.co/9Ht6dPkW/robbery.webp",
               "https://i.ibb.co/Zp301w42/sexual-assault.webp",
               "https://i.ibb.co/QSLqqW1/aggravated-assault.webp",
               "https://i.ibb.co/KjRwfd3M/burglary.webp",
               "https://i.ibb.co/XkxDPSj8/motor-vehicle-theft.webp",
               "https://i.ibb.co/bMSLDpkq/murder.webp",
               "https://i.ibb.co/JFgZf7w7/larceny.webp"]


def load_memphis_population_data():
    # Collect Memphis population figures from the supporting spreadsheets
    script_dir = Path(__file__).parent
    memphis_folder = script_dir.parent / "Memphis, Tennessee"
    
    population = {}
    
    file_2010_2020 = memphis_folder / "tennessee_city_population_2010_2020.xlsx"
    if file_2010_2020.exists():
        df = pd.read_excel(file_2010_2020, header=None)
        for i, row in df.iterrows():
            if 'Memphis city' in str(row[0]):
                for year_offset, col_idx in enumerate(range(2, 12)):
                    year = 2010 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    file_2020_2024 = memphis_folder / "tennessee_city_population_2020_2024.xlsx"
    if file_2020_2024.exists():
        df = pd.read_excel(file_2020_2024, header=None)
        for i, row in df.iterrows():
            if 'Memphis city' in str(row[0]):
                for year_offset, col_idx in enumerate(range(2, 7)):
                    year = 2020 + year_offset
                    pop = row[col_idx]
                    if pd.notna(pop):
                        population[year] = int(pop)
                break
    
    return population


def _sanitize_response_text(text: str) -> str:
    # Normalize model responses into plain text suitable for parsing
    text = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).strip('`'), text)
    text = text.strip('`\n\r ')

    text = re.sub(r"\s*[-:–—]\s*", ",", text)

    return text


def _extract_filename_from_url(url: str) -> str:
    # Convert the hosted image URL into a CSV filename
    name = Path(url).name
    stem = Path(name).stem
    return f"{stem}.csv"


def _write_csv_from_text(csv_path: Path, text: str, population_data: dict = None) -> None:
    # Parse AI text into year/count rows and persist them to CSV
    lines = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        line = re.sub(r"^[\-\*\u2022]\s*", "", line)

        if "," in line:
            parts = [p.strip() for p in line.split(",") if p.strip()]
        else:
            parts = [p.strip() for p in re.split(r"\s+|\t", line) if p.strip()]

        if len(parts) >= 2:
            year = parts[0]
            value = parts[1]
            if re.match(r"^\d{4}$", year):
                lines.append((year, value))
            else:
                digits = [p for p in parts if re.match(r"^\d{4}$", p)]
                if digits:
                    y = digits[0]
                    try:
                        idx = parts.index(y)
                        val = parts[idx + 1] if idx + 1 < len(parts) else parts[0]
                    except ValueError:
                        val = parts[-1]
                    lines.append((y, val))

    if not lines:
        tokens = re.findall(r"(\d{4})[^\d]{0,10}(\d+)", text)
        for y, v in tokens:
            lines.append((y, v))

    lines = [(y, v) for y, v in lines if 2014 <= int(y) <= 2024]

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if lines:
            if population_data:
                writer.writerow(["year", "count", "population"])
                for y, v in lines:
                    pop = population_data.get(int(y), "")
                    writer.writerow([y, v, pop])
            else:
                writer.writerow(["year", "count"])
                for y, v in lines:
                    writer.writerow([y, v])
        else:
            writer.writerow(["response"])
            writer.writerow([text])


def update_existing_csvs_with_population():
    # Backfill population data into Memphis CSV outputs when missing
    population = load_memphis_population_data()
    output_folder = Path(__file__).parent.parent / "Memphis, Tennessee" / "output"
    
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
    
    if len(sys.argv) > 1 and sys.argv[1] == "--update-population":
        print("Updating existing CSVs with population data...")
        update_existing_csvs_with_population()
        sys.exit(0)
    
    population_data = load_memphis_population_data()
    print(f"Loaded Memphis population data for years: {sorted(population_data.keys())}")

    for photo_link in photo_links:
        completion = client.chat.completions.create(
            model="google/gemini-3-pro-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Use the image provided to create a csv file. Grab data from 2014 to 2024. The first column of the csv should be the year and the second column should be how many times a given crime was commited in that year."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": photo_link
                            },
                        },
                    ],
                }
            ],
        )

        raw_content = completion.choices[0].message.content
        if isinstance(raw_content, list) or isinstance(raw_content, dict):
            try:
                if isinstance(raw_content, list):
                    parts = []
                    for item in raw_content:
                        if isinstance(item, dict) and "text" in item:
                            parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            parts.append(item)
                    model_text = "\n".join(parts)
                else:
                    model_text = str(raw_content)
            except Exception:
                model_text = str(raw_content)
        else:
            model_text = str(raw_content)

        clean = _sanitize_response_text(model_text)
        filename = _extract_filename_from_url(photo_link)
        out_path = Path(__file__).resolve().parent.parent / "Memphis, Tennessee" / "output" / filename
        _write_csv_from_text(out_path, clean, population_data)
        print(f"Wrote: {out_path}")
