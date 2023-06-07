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

To run the program stand at the root of the directory, and run
python src\main.py

This will launch the application in it's default state, there are two args that you may use to run the application -fs/--from_scratch, which initiates the twitter database without a dataset. The other one is -r/--reset, which will reset the database. from scratch or from dataset (default)

example: from scratch and reset
python src\main.py -fs -r
