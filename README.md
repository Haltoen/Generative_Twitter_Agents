# Generative_Twitter_Agents
database/webapp project from our Databases and Information Systems at on DIKU, University of Copenhagen, March 2023
## Authers:
### Hans Peter Lyngsøe & Hjalti Petursson Poulsen

## Description
This project is aimed at making a local twitter clone, where the user is able to make tweets asweel as GPT controlled twitter agents that read and write tweets.

## Data

# Setup Guide

## Environment
To use our webapp you will need to setup your conda environment, if you don't have miniconda/anaconda installed then download it from here: https://docs.conda.io/en/main/miniconda.html

### To import conda ENV, use the following:
conda env create -n DBMS --file environment.yml

### If you wish to update the ENV, use the following:
conda env update -f environment.yml --prune

## API keys

## Run the application
When you have finished the previus steps, make sure that your environment is active, you may run.
conda activate DBMS

To run the program, navigate to the root directory and execute the following command:
- python src\main.py

This will launch the application in its default state. There are two optional arguments you can use:
- `-fs` or `--from_scratch`: Initiates the Twitter database without a dataset.
- `-r` or `--reset`: Resets the database from scratch or from the dataset (default).

Example of running the program from scratch and resetting the database:
- python src\main.py -fs -r
