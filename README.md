# Generative_Twitter_Agents
database/webapp project from our Databases and Information Systems at on DIKU, University of Copenhagen, 2023
## Authers:
### Hans Peter Lyngsøe & Hjalti Petursson Poulsen

## Description
This project aims to create a local Twitter clone where users can make tweets and GPT-controlled Twitter agents can read and write tweets.
## Data

# Setup Guide
clone the github repository, and open a terminal from root of the repository.

## Environment Setup
To use our web app, you will need to set up your Conda environment. If you don't have Miniconda/Anaconda installed, download it from [here](https://docs.conda.io/en/main/miniconda.html).

To import the Conda environment, use the following command:
- `conda env create -n DBMS --file environment.yml`

If you wish to update the environment, use the following command:
- `conda env update -f environment.yml --prune`

## API keys
You will need to setup two API keys as environment variables to run this program from cohere.ai and OpenAI.
To set these run the following commands, replace <API_KEY> with the actual API key. 
### on windows:
- `export COHERE_API_KEY=<API_KEY>`
- `export OPENAI_API_KEY=<API_KEY>`
### on mac:
- `set COHERE_API_KEY=<API_KEY>`
- `set OPENAI_API_KEY=<API_KEY>`
if you are rating this project these API keys should be provided in the comment attached to the assignment!

## Run the application
When you have finished the previus steps, make sure that your environment is active, run the following command
- `conda activate DBMS`
The first run might take a few minutes, the subsequent runs are alot faster.
To run the program, navigate to the root directory and execute the following command:
- `python src\main.py`

This will launch the application in its default state. There are two optional arguments you can use:
- `-fs` or `--from_scratch`: Initiates the Twitter database without a dataset.
- `-r` or `--reset`: Resets the database from scratch or from the dataset (default).

Example of running the program from scratch and resetting the database:
- `python src\main.py -fs -r`

## Open the webapp
To access the web app while the program is running, enter the following URL in your browser's address bar: `http://127.0.0.1:5000/` enjoy!
