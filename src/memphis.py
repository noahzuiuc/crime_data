import os
from dotenv import load_dotenv
from openai import OpenAI
import re
import csv
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

photo_links = ["https://i.ibb.co/9Ht6dPkW/robbery.webp",
               "https://i.ibb.co/Zp301w42/sexual-assault.webp",
               "https://i.ibb.co/QSLqqW1/aggravated-assault.webp",
               "https://i.ibb.co/KjRwfd3M/burglary.webp",
               "https://i.ibb.co/PGFrpGmm/grand-theft-auto.webp",
               "https://i.ibb.co/G40d4K7p/homicide.webp",
               "https://i.ibb.co/JFgZf7w7/larceny.webp"]

def _sanitize_response_text(text: str) -> str:
    """Remove markdown/code fences and normalize separators to commas."""
    # Remove triple backtick fences and language hints
    text = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).strip('`'), text)
    text = text.strip('`\n\r ')

    # Replace common separators like ' - ', ' : ', '—' and ' – ' with a comma
    text = re.sub(r"\s*[-:–—]\s*", ",", text)

    return text


def _extract_filename_from_url(url: str) -> str:
    """Return a filename (without extension) for the csv based on the image url path.

    Example: https://.../robbery.webp -> robbery.csv
    """
    name = Path(url).name
    stem = Path(name).stem
    return f"{stem}.csv"


def _write_csv_from_text(csv_path: Path, text: str) -> None:
    """Attempt to parse lines of 'year,value' from text and write to csv_path.

    If text already contains commas, use them. Otherwise try to split on whitespace.
    """
    lines = []

    # Split into lines and clean each
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Skip markdown headings or bullet markers
        line = re.sub(r"^[\-\*\u2022]\s*", "", line)

        # If line contains a comma, assume it's already CSV-like
        if "," in line:
            parts = [p.strip() for p in line.split(",") if p.strip()]
        else:
            # Try splitting on whitespace (e.g., '2014 123') or on tab
            parts = [p.strip() for p in re.split(r"\s+|\t", line) if p.strip()]

        # Expect at least year and value
        if len(parts) >= 2:
            year = parts[0]
            value = parts[1]
            # Basic validation: year is 4 digits
            if re.match(r"^\d{4}$", year):
                lines.append((year, value))
            else:
                # Maybe the year is second (e.g., 'Robbery 2014 123') - try to find a 4-digit token
                digits = [p for p in parts if re.match(r"^\d{4}$", p)]
                if digits:
                    y = digits[0]
                    # choose the token after year as value if available
                    try:
                        idx = parts.index(y)
                        val = parts[idx + 1] if idx + 1 < len(parts) else parts[0]
                    except ValueError:
                        val = parts[-1]
                    lines.append((y, val))

    # If nothing parsed, try to extract all 'YYYY' and numbers pairs from the whole text
    if not lines:
        tokens = re.findall(r"(\d{4})[^\d]{0,10}(\d+)", text)
        for y, v in tokens:
            lines.append((y, v))

    # Post-process: filter to only keep years between 2014 and 2024
    lines = [(y, v) for y, v in lines if 2014 <= int(y) <= 2024]

    # If still nothing, write the raw text into a single-cell csv
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if lines:
            writer.writerow(["year", "count"])
            for y, v in lines:
                writer.writerow([y, v])
        else:
            writer.writerow(["response"])
            writer.writerow([text])


for photo_link in photo_links:
    completion = client.chat.completions.create(
        model="google/gemini-2.5-pro",
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
    _write_csv_from_text(out_path, clean)
    print(f"Wrote: {out_path}")
