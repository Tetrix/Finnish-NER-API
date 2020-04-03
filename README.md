# Finnish-NER-API
This repository contains an API for using the Finnish NER system

# Requirements
1. pytorch
2. pytorch-crf
3. gensim
4. morfessor
5. flask

# Download resources
The pretrained word embeddings can be downloaded from the following link: https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.fi.300.bin.gz .

You need to place the embeddings in the `weights` directory.

# Usage
There are two models trained: `model_lower` and `model_upper`. The first one is trained on lower case data and without punctuation. 
The second one is trained on data that contains both lower and upper case letter together with punctuation.

To switch between models, change the flag `lowercase_model` in `config/params.py` file.
By default the `lowercase_model` is used.

To start the server run: `python run_server.py`.

To evaluate a document run: `python process_request.py --input input_document.txt --output output_document.txt`

The format of the input file should be as following:
Note: leave two empty rows at the end of the file

`
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
`
