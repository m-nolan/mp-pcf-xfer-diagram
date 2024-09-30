# Minnesota PCF Transfer Diagram

Michael Nolan

2024-09-29

## Description

This script processes inter-committee (political committees, funds, IE committees, etc) transfers filed with the MN campaign finance board into json files enabling d3 force-directed network diagrams. These diagrams show how cash is flowing between MN political entities, elucidating funding sources and sinks in the state's politics

## Installation
- Clone this repo
- Requirements: pandas, numpy

## Use
- Access MN CFB .mdb file for the relevant time period
- Write out .mdb tables as .csv files using TKTKTK
- run: `python generate_xfer_json.py data_dir`
	- Parameters:
		- -o/--output_dir: sets data output directory. Defaults to data_dir
		- -m/--min_val: minimum transfer value included in dataset
		- --filetyle: 'json' or 'csv'

