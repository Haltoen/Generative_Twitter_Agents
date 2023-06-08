import argparse
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.resolve() # src
sys.path.append(str(parent_dir))

from web_app.run_app import start_app

# Create an arg parser
parser = argparse.ArgumentParser()

# named args
parser.add_argument('-fs', '--from_scratch', action='store_true', help='pass boolean, if True then use empty database template')
parser.add_argument('-r', '--reset', action='store_true', help='pass boolean, if True then reset database')

# Parse command-line args
args = parser.parse_args()
from_scratch = args.from_scratch
reset = args.reset

start_app(from_scratch, reset)

