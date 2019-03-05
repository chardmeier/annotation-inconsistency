#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
from bs4 import BeautifulSoup


def create_document(dir, doc):

    document = []
    with open(dir + "/" + doc, "r", encoding="utf-8") as en_xml:
        soup = BeautifulSoup(en_xml, "xml")
        # make doc out of _words.xml files
        for w in soup.find_all("word"):
            document.append(w.string)
    return document


def make_sentences_spans(doc_id, markables):
    """
    :param doc_id: id of current document
    :param markables: corresponding annotation from parcor-full which contains the sentence info
    :return: dictionary of spans (with indexing of sentences starting at 1 as in protest/parcor)
    """

    sentences_spans = {}

    with open(markables + "/" + doc_id[:-10] + "_" + "sentence_level.xml", "r", encoding="utf-8") as key:
        soup = BeautifulSoup(key, "xml")
        for m in soup.find_all("markable"):
            span = re.match(r'[a-z]+_([0-9]+)\.\.[a-z]+_([0-9]+)', m['span'])
            if span:
                sent_id = int(m['orderid'])
                start = int(span.group(1))
                end = int(span.group(2))
                sentences_spans[sent_id] = (start, end)
            else:
                word = re.match(r'[a-z]+_([0-9]+)', m['span'])
                sent_id = int(m['orderid'])
                start = int(word.group(1))
                end = start + 1
                sentences_spans[sent_id] = (start, end)
    return sentences_spans


def make_sentences(doc, spans):

    text_document = []
    for span in sorted(spans.keys()):
        start = spans[span][0]-1
        end = spans[span][1]
        sentence = []
        for i in range(start, end):
            sentence.append(doc[i])
        sentence.append("\n")
        text_document.append(sentence)
    return text_document



if len(sys.argv) != 3:
        sys.stderr.write('Usage: {} {} {} \n'.format(sys.argv[0], "lang(EN|DE)", "subcorpus(news|TED|DiscoMT)"))

        sys.exit(1)

lang = sys.argv[1]
subcorpus = sys.argv[2]

path_parcorful = "/Users/xloish/PycharmProjects/testsuitewmt18/parcor-full/corpus"

data_dir = path_parcorful + "/" + subcorpus + "/" + lang + "/" + "Basedata"
mark_dir = path_parcorful + "/" + subcorpus + "/" + lang + "/" + "Markables"

out = "/Users/xloish/PycharmProjects/annotation-inconsistency/parcorfull_textdata"

files = os.listdir(data_dir)

for file in files:

    if file.endswith("xml"):
        out_file = open(out + "/" + subcorpus + "_" + lang + "_" + file[:-10] + ".txt", "w", encoding="utf-8")

        document = create_document(data_dir, file)
        s_spans = make_sentences_spans(file, mark_dir)
        text = make_sentences(document, s_spans)
        for sentence in text:
            line = " ".join(sentence)
            out_file.write(line)
        out_file.close()

