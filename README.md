This project was built and tested with python 3.12.7, compatibility with other versions may vary.  
This project was built and tested using Windows 11, compatibility with other operating systems may vary.

Create a virtual environment for the project (in the root directory)
```bash
python -m venv crime_data_env
```

Activate the environment
```bash
# Windows
crime_data_env\Scripts\activate.bat
# Mac/Linux
source crime_data_env/bin/activate
```

Install the requirements (in the src directory)
```bash
pip install -r requirements.txt
```

Rename .env.example to .env and supply an openrouter API key

In the src directory:
To extract data for a given city run
```bash
python <city-name>.py
```

Once the data is extracted, combine it by running
```bash
python data_combiner.py
```

To run the dashboard use:
```bash
streamlit run dashboard.py
```

NOTE: For Memphis, images must be uploaded to an image host and the array in memphis.py at line 21 must be updated.