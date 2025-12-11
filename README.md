This project was built and tested with python 3.12.7, compatibility with other versions may vary.  
This project was built and tested using Windows 11 and MacOS 26.1, compatibility with other operating systems may vary.

Each city folder contains an input folder for the data sources. Once a city's script has been run it will populate the output folder (however it is pre-populated with current data for convenience).


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

Rename .env.example to .env and supply an openrouter API key

In the src directory:  
Install the requirements
```bash
pip install -r requirements.txt
```

Show the dashboard with the already processed data
```bash
streamlit run dashboard.py
```

Run the data processing and then show the dashboard (costs money in OpenRouter inference credits)
*This method is for convenience, but if there is an error (which can happen randomly sometimes with OpenRouter) it has to be entirely rerun. It is recommended to run the individual steps as shown further down.
```bash
python full_run.py
```

OR

You may choose to execute the steps individually (again in the src directory):

To extract data for a given city run
```bash
python <city-name>.py
```

Once the data for all cities has been extracted, combine the data by running
```bash
python data_combiner.py
```

To run the dashboard use:
```bash
streamlit run dashboard.py
```


In the src directory:
Do all of the above in one step:


NOTES:  
For Memphis, images must be uploaded to an image host and the array in memphis.py at line 21 must be updated. I have already uploaded the images so you may leave the links as is if you are not trying to introduce new data. 
Los Angeles data is for Los Angeles County, all other cities data is for the city proper.
