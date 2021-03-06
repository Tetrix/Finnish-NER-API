# encoding: utf-8

import os
import operator
import flask

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torch.autograd as autograd

import numpy as np
from argparse import ArgumentParser
import gensim
import morfessor
import pickle

from model import NERModel
from config.params import *



app = flask.Flask(__name__)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

torch.manual_seed(0)

print(device)


def load_data(data_path):
    words = []
    data = []
    with open(data_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            if line != '\n':
                words.append(line.rstrip())
            else:
                words.insert(0, '<start>')
                words.append('<end>')
                data.append(words)
                words = []
    return data


def combine_data(indexed_data, indexed_char_train, indexed_morph_train, MAX_SEQ_LENGTH):
    res = []
    for seq in range(len(indexed_data)):
        if len(indexed_data[seq]) <= MAX_SEQ_LENGTH:
            res.append((indexed_data[seq], indexed_char_train[seq], indexed_morph_train[seq]))
    return res


def prepare_sequence(seq, embeddings):
    res = []
    for w in seq:
        try:
            res.append(embeddings[w])
        except:
            res.append(np.random.normal(scale=0.6, size=(300, )))
    res = autograd.Variable(torch.FloatTensor(res))
    return res


def prepare_char_sequence(word, to_idx):
    res = []
    for char in word:
        try:
            res.append(to_idx[char])
        except:
            char = list(to_idx.keys())[0]
            res.append(to_idx[char])
    return autograd.Variable(torch.LongTensor(res))


def prepare_morph_sequence(word, to_morph, to_idx):
    res = []
    morphs = to_morph[word]
    for morph in morphs.split(' '):
        try:
            res.append(to_idx[morph])
        except:
            morph = list(to_idx.keys())[0]
            res.append(to_idx[morph])
    return autograd.Variable(torch.LongTensor(res))


def data_to_idx(data, embeddings):
    res = []
    for seq in range(len(data)):
        res.append(prepare_sequence(data[seq], embeddings))
    return res


def char_to_idx(data, char2idx):
    res = []
    for seq in range(len(data)):
        temp = []
        for w in data[seq]:
            temp.append(prepare_char_sequence(w, char2idx))
        res.append(temp)
    return res


def morph_to_idx(data, morph2idx, word2morph):
    res = []
    for seq in range(len(data)):
        temp = []
        for w in data[seq]:
            temp.append(prepare_morph_sequence(w, word2morph, morph2idx))
        res.append(temp)
    return res


def word_to_morph(data_morphs):
    word2morph = {}
    word2morph['<start>'] = '<start>'
    word2morph['<end>'] = '<end>'

    for seq in data_morphs:
        word = ''
        segments = seq.split(' ')
        segments_with_boundaries = add_subword_boundaries(segments)

        for segment in segments:
            word += segment
        word2morph[word] = segments_with_boundaries
    return word2morph


# convert words and tags to indices
def encode_data(whole_data):
    word2idx = {}
    idx2word = {}
    char2idx = {}
    idx2char = {}

    for sent in whole_data:
        for word in sent:
            if word not in word2idx:            
                word2idx[word] = len(word2idx) + 1
                idx2word[len(idx2word) + 1] = word
            for char in word:
                if char not in char2idx:
                    char2idx[char] = len(char2idx) + 1
                    idx2char[len(idx2char) + 1] = char
    return word2idx, idx2word, char2idx, idx2char



# add subword boundaries, example: liiketoiminta+ +yksikkö
def add_subword_boundaries(subwords):
    res = ''
    if len(subwords) == 1:
        res = subwords[0]
    else:
        for i in range(len(subwords)):
            if i == 0:
                res += subwords[i] + '+'
            elif i < len(subwords) - 1:
                res += ' +' + subwords[i] + '+'
            elif i == len(subwords) - 1:
                res += ' +' + subwords[i]
    return res


# pad chars and morphs
# idx = 2 for chars, 3 for morphs
def pad_subwords(subwords):   
    subword_lengths = []
    for seq in subwords:
        subword_lengths.append(seq.size(0))
    max_subword_length = max(subword_lengths)
    
    for seq in range(len(subwords)):
        pad_size = max_subword_length - subwords[seq].size(0)
        pad_tensor = torch.zeros([pad_size], dtype=torch.int64)

        if pad_size != 0:
            subwords[seq] = torch.cat((subwords[seq], pad_tensor), 0)
    

    pad_subword_seqs = torch.stack(subwords)
    pad_subword_seqs = pad_subword_seqs.unsqueeze(1)
    
    return pad_subword_seqs



def evaluate_document(word_num_layers, char_num_layers, morph_num_layers, word_hidden_size, char_hidden_size, morph_hidden_size, batch_size, indexed_data, data, model, device):
    #with open (file, 'w', encoding='utf-8') as f:
    result = []

    for num, sent in enumerate(indexed_data):
        json_sent = []
        sentence = sent[0].to(device)
        chars = sent[1]
        morphs = sent[2]

        word_hidden = model.init_hidden(word_num_layers, word_hidden_size, batch_size, device)
        char_hidden = model.init_hidden(char_num_layers, char_hidden_size, batch_size, device)
        morph_hidden = model.init_hidden(morph_num_layers, morph_hidden_size, batch_size, device)

        pad_char_seqs = pad_subwords(chars).to(device)
        pad_morph_seqs = pad_subwords(morphs).to(device)

        sentence = sentence.unsqueeze(1)

        emissions = model(sentence, [len(sentence)], pad_char_seqs, [pad_char_seqs.size(0)], pad_morph_seqs, [pad_morph_seqs.size(0)], word_hidden, char_hidden, morph_hidden, batch_size)

        predictions = model.crf.decode(emissions)[0]

        for i in range(len(data[num])):
            word = data[num][i].rstrip()
            tag = idx2tag[predictions[i]]

            if word != '<start>' and word != '<end>':
                json_sent.append({'word': word, 'tag': tag})
        
        if len(json_sent) != 0:
            result.append({'sentence': json_sent})
      
    return result





@app.route("/predict", methods=["POST"])
def evaluate():
    # Initialize the data dictionary that will be returned from the view
    data = {'success': False}

    if flask.request.method == 'POST':
        if flask.request.files.get('file'):
            input_data_path = flask.request.files['file'].read()
            
            input_data = load_data(input_data_path)
              
            # segment data into morphs
            input_data_morphs = []
            for sent in input_data:
                for word in sent:
                    input_data_morphs.append(' '.join(morfessor_model.viterbi_segment(word)[0]))
    
        
            word2morph = word_to_morph(input_data_morphs)

            indexed_data = data_to_idx(input_data, embeddings)
            indexed_char = char_to_idx(input_data, char2idx)
            indexed_morph = morph_to_idx(input_data, morph2idx, word2morph)
            indexed_input_data = combine_data(indexed_data, indexed_char, indexed_morph, MAX_SEQ_LENGTH)

    
            print('Processing the document')
            result = evaluate_document(word_num_layers, char_num_layers, morph_num_layers, word_hidden_size, char_hidden_size, morph_hidden_size, batch_size, indexed_input_data, input_data, model, device)
            print('Done')
            
            data['predictions'] = result
            data['success'] = True
    
            return flask.jsonify(data)


if __name__ == '__main__':
    print('Loading embeddings...')
    #embeddings = gensim.models.KeyedVectors.load_word2vec_format('data/embeddings/fin-word2vec.bin', binary=True, limit=100000)
    embeddings = gensim.models.fasttext.load_facebook_vectors('weights/cc.fi.300.bin')
    print('Finished loading embeddings')

    #load the morfessor model
    io = morfessor.MorfessorIO()
    morfessor_model = io.read_binary_model_file('weights/morfessor_0.1.bin')

    idx2tag = {1: 'O', 2: 'B-ORG', 3: 'I-ORG', 4: 'B-PRO', 5: 'B-PER', 6: 'I-PER', 7: 'I-PRO', 8: 'B-LOC', 9: 'B-DATE', 10: 'B-EVENT', 11: 'I-LOC', 12: 'I-EVENT', 13: 'I-DATE'}
    num_tags = len(idx2tag) + 1
   
    #load indices
    if lowercase_model == False:
        with open('weights/char_dict_upper.pkl', 'rb') as f:
            char2idx = pickle.load(f)    
        with open('weights/morph_dict_upper.pkl', 'rb') as f:
            morph2idx = pickle.load(f)
    else:
        with open('weights/char_dict_lower.pkl', 'rb') as f:
            char2idx = pickle.load(f)    
        with open('weights/morph_dict_lower.pkl', 'rb') as f:
            morph2idx = pickle.load(f)

    
    # initialize the model
    print('Initializing the model...')
    model = NERModel(word_embedding_dim, char_embedding_dim, morph_embedding_dim, word_hidden_size, char_hidden_size, morph_hidden_size, 
                    len(char2idx), len(morph2idx), num_tags, word_num_layers, char_num_layers, morph_num_layers, dropout_prob).to(device)
    print('Done')

 
    # load the model
    print('Loading the model...')
    if lowercase_model == False:
        model.load_state_dict(torch.load('weights/model_upper.pt'))
    else:
        model.load_state_dict(torch.load('weights/model_lower.pt'))
    print('Done')

    model.eval()
    batch_size = 1


    print('Server running') 
    app.run(debug=False)
