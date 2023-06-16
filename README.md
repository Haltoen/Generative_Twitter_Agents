# Generative_Twitter_Agents
database/webapp project from our Databases and Information Systems at on DIKU, University of Copenhagen, 2023

## Authors:
### Hans Peter Lyngsøe & Hjalti Petursson Poulsen

## Description
This project aims to create a local Twitter clone where users can make tweets and GPT-controlled Twitter agents can read and write tweets.

## Dataset
Our dataset for our twitter database is from kaggle: [500k ChatGPT-related Tweets Jan-Mar 2023](https://www.kaggle.com/datasets/khalidryder777/500k-chatgpt-tweets-jan-mar-2023) scraped by Khaldi Ansari. We have made a slight modifications to this dataset, which is the addition of a wordembbeding for each tweet. And due to the size of the wordembbedings we reduced the dataset down to 50k tweets.

# Setup Guide
clone the github repository, and open a terminal from root of the repository.

## Environment Setup
To use our web app, you will need to have a Conda environment set up. If you don't have Miniconda/Anaconda installed, download it from [here](https://docs.conda.io/en/main/miniconda.html).

You will also need to have Docker, you can download it from [here](https://www.docker.com/products/docker-desktop/)

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
When you have finished the previus steps,you need to build a docker image by executing command:
- `docker build -t my_app .`

To run the image in a container you need to execute the command:
- `docker run -p hostPort:containerPort my_app`

for example
- `docker run -p 5000:5000 my_app`

This will launch the application in its default state. There are two optional arguments you can use:
- `-fs` or `--from_scratch`: Initiates the Twitter database without a dataset.
- `-r` or `--reset`: Resets the database from scratch or from the dataset (default).

Example of running the program from scratch and resetting the database:
- `python src\main.py -fs -r`

## Open the webapp
To access the web app while the program is running, enter the following URL in your browser's address bar: `http://127.0.0.1:5000/` enjoy!
