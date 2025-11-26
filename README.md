This project was developed python 3.12.7. Compatibility with other version may vary.

Create a virtual environment for the project (in the root directory)
```bash
python -m venv crime_data_env
```

Activate the environment
```bash
# Mac/Linux
source crime_data_env/bin/activate
# Windows
crime_data_env\Scripts\activate.bat
```

Install the requirements (in the src directory)
```bash
pip install -r requirements.txt
```

Rename .env.example to .env and supply an openrouter API key