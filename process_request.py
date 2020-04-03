'''

This script takes two input arguments:
--input - input file to be evaluated
--output - path where the output will be stored


The format of the input file should be as following:
Note: leave two empty rows at the end of the file
**************************************
Kun
Turun
akatemian
ensimmäinen
fysiikan
ja
kasvitieteen
professori
Georgius
Alanus
siirtyi
teologiseen
tiedekuntaan

Kolmen
ehdokkaan
joukosta
pätevimmäksi
katsottiin
Thauvonius
,
ja
hän
saikin
nimityksen
tähän
virkaan
1649
.


**************************************

The output will be in the following format:

**************************************
Kun	O
Turun	B-ORG
akatemian	I-ORG
ensimmäinen	O
fysiikan	O
ja	O
kasvitieteen	O
professori	O
Georgius	B-PER
Alanus	I-PER
siirtyi	O
teologiseen	O
tiedekuntaan	O

Kolmen	O
ehdokkaan	O
joukosta	O
pätevimmäksi	O
katsottiin	O
Thauvonius	B-PER
,	O
ja	O
hän	O
saikin	O
nimityksen	O
tähän	O
virkaan	O
1649	B-DATE
.


**************************************

'''

import json
import requests
from argparse import ArgumentParser

URL = 'http://127.0.0.1:5000/predict'


def predict_result(input_path, output_path):
    # Initialize image path
    input_document = {'file': input_path}
    r = requests.post(URL, files=input_document).json()
    

    # Ensure the request was successful.
    if r['success']:
        #save output
        with open(output_path, 'w') as f:
            json.dump(r, f, ensure_ascii=False)
    else:
        print('Request failed')



if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-i", "--input", dest="input",
                        help="input document to be evaluated", metavar="INPUT", required=True)

    parser.add_argument("-0", "--output", dest="output",
                        help="Path to file where the result will be stored", metavar="OUTPUT", required=True)


    args = parser.parse_args()    
    input_path = args.input
    output_path = args.output

    predict_result(input_path, output_path)
    
