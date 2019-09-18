import sys
import os
import argparse
import fasttext
import json
import re
import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable
from torch.nn import functional as F
from gensim.models import KeyedVectors
from nltk.stem.porter import PorterStemmer
class Embeddings(object):
    """Class for creating an embedding vector with the pretrained Word2Vec embeddings.

    Example usage:
        Use torch.nn.Embed layer (with embedding size of 300) and fix the pretrained embeddings by
        `
        with torch.no_grad():
            model.embed.weight.data.copy_(torch.from_numpy(vectors))
            model.embed.weight.requires_grad = False
        `

    """

    def __init__(self,filepath):
        self.model = KeyedVectors.load_word2vec_format(os.path.dirname(os.path.realpath(__file__)) +filepath, binary=True)

    def create_embeddings(self, token2ind):
        vectors = []
        unknown_vector = np.random.uniform(-0.05, 0.05, 300).astype(np.float32)
        for token, ind in token2ind.items():
            if token == '<unk>':
                vectors.append(list(unknown_vector))
            elif token == '<pad>':
                vectors.append(list(np.zeros(300).astype(np.float32)))
            elif ind == 0:
                continue
            else:
                vectors.append(list(self.model[token]))

        vectors = np.stack(vectors, axis=0)
        return vectors
class Logger(object):
    '''
    Export print to logs.
    '''

    def __init__(self, file_loc):
        self.terminal = sys.stdout
        self.log = open(file_loc, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass
class InputParser(object):

    def __init__(self, token2ind):
        self.token2ind = token2ind    
        self.stemmer = PorterStemmer()

    def word2id(self,word):
        if word in self.token2ind.keys():
            return self.token2ind[word]
        else:
            return 0

    def sentence2id(self,word_list):
        sentence = self.stemmer.stem(' '.join(word_list)) 
        sentence_id = [self.word2id(word) for word in self.clean_text(sentence).split()]
        return sentence_id

    def clean_text(self,text):

        # Clean the text
        text = re.sub(r"[^A-Za-z0-9^,!.\/'+-=]", " ", text)
        text = re.sub(r"what's", "what is ", text)
        text = re.sub(r"\'s", " ", text)
        text = re.sub(r"\'ve", " have ", text)
        text = re.sub(r"can't", "cannot ", text)
        text = re.sub(r"n't", " not ", text)
        text = re.sub(r"i'm", "i am ", text)
        text = re.sub(r"\'re", " are ", text)
        text = re.sub(r"\'d", " would ", text)
        text = re.sub(r"\'ll", " will ", text)
        text = re.sub(r",", " ", text)
        text = re.sub(r"\.", " ", text)
        text = re.sub(r"!", " ! ", text)
        text = re.sub(r"\/", " ", text)
        text = re.sub(r"\^", " ^ ", text)
        text = re.sub(r"\+", " + ", text)
        text = re.sub(r"\-", " - ", text)
        text = re.sub(r"\=", " = ", text)
        text = re.sub(r"'", " ", text)
        text = re.sub(r"(\d+)(k)", r"\g<1>000", text)
        text = re.sub(r":", " : ", text)
        text = re.sub(r" e g ", " eg ", text)
        text = re.sub(r" b g ", " bg ", text)
        text = re.sub(r" u s ", " american ", text)
        text = re.sub(r"\0s", "0", text)
        text = re.sub(r" 9 11 ", "911", text)
        text = re.sub(r"e - mail", "email", text)
        text = re.sub(r"j k", "jk", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text

def load_json(file_loc, mapping=None, reverse=False, name=None):
    '''
    Load json file at a given location.
    '''

    with open(str(file_loc), 'r') as file:
        data = json.load(file)
        file.close()
    if reverse:
        data = dict(map(reversed, data.items()))
    print_logs(data, mapping, name)
    return data


def print_logs(data, mapping, name, keep=3):
    '''
    Print detailed information of given data iterator.
    '''

    print('Statistics of {}:'.format(name))
    try:
        count = 0
        for key in data:
            print('* Number of data in class {}: {}'.format(mapping[int(key)][:keep], len(data[key])))
            count += len(data[key])
        print('+ Total: {}'.format(count))
    except:
        print('* Class: {}'.format(data))
        print('+ Total: {}'.format(len(data)))


def print_statement(statement, isCenter=False, symbol='=', number=15, newline=False):
    '''
    Print required statement in a given format.
    '''
    if newline:
        print()
    if number > 0:
        prefix = symbol * number + ' '
        suffix = ' ' + symbol * number
        statement = prefix + statement + suffix
    if isCenter:
        print(statement.center(os.get_terminal_size().columns))
    else:
        print(statement)


def print_flags(args):
    """
    Print all entries in args variable.
    """
    for key, value in vars(args).items():
        print(key + ' : ' + str(value))


def print_result(result, keep=3):
    """
    Print result matrix.
    """

    if type(result) == dict:
        # Individual result.
        for key in result:
            prec = result[key]['precision']
            rec = result[key]['recall']
            f1 = result[key]['f1score']
            key = key.replace('__label__', '')[:keep]
            print('* {} PREC: {:.2f}, {} REC: {:.2f}, {} F1: {:.2f}'.format(key, prec, key, rec, key, f1))
    elif type(result) == tuple:
        # Overall result.
        print('Testing on {} data:'.format(result[0]))
        print('+ Overall ACC: {:.3f}'.format(result[1]))
        assert result[1] == result[2]
    else:
        raise TypeError

def print_value(name,value):
    print(name + f':{value}')

def convert_to_txt(data, label, file_loc):
    '''
    Convert data to fasttext training format.
    '''

    with open(file_loc, mode='w', encoding='utf-8') as file:
        for key in data:
            name = '__label__' + label[int(key)]
            for query in data[key]:
                file.write('{}\t{}\n'.format(name, ' '.join(query)))
        file.close()

def convert_to_tensor(data,label_map,token2ind):
    parser = InputParser(token2ind)
    inputs = []
    outputs = []
    for i in range(len(label_map)):
        for line in data[str(i)]:
            inputs.append(parser.sentence2id(line))
            outputs.append(str(i))
    max_length = np.max([len(line) for line in inputs])
    input_tensor = torch.ones(len(inputs),max_length)
    output_tensor = torch.zeros(len(inputs))
    for i, sentence in enumerate(inputs):
        output_tensor[i] = int(outputs[i])
        for j,value in enumerate(sentence):
            input_tensor[i][j]=value
    return input_tensor,output_tensor


    
