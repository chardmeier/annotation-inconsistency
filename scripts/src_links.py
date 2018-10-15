#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extracts links from parcor-full

!!!!!NOTE: in parcorfull numbering for sentences starts at 0 but numbering for words starts at 1
"""

import sys, re
from bs4 import BeautifulSoup


def create_document(dir, doc):

    document = []
    with open(dir + "/" + doc, "r", encoding="utf-8") as en_xml:
        soup = BeautifulSoup(en_xml, "xml")
        # make doc out of _words.xml files
        for w in soup.find_all("word"):
            document.append(w.string)
    return document


def read_alignments(f):

    giza_alignments = open(f, "r", encoding="utf=8")
    all_aligns = {}
    # 0-0 1-1 2-2 3-3 4-4 5-5 6-5 8-6 12-7 7-8 9-9 13-10 14-11 15-13
    sent = 0
    for line in giza_alignments:
        aligns = line.strip('\n').split(" ")
        all_aligns[sent] = aligns
        sent += 1
    giza_alignments.close()
    return all_aligns


def make_sentences_spans(doc_id, markables):
    """
    :param doc_id: id of current document
    :param markables: corresponding annotation from parcor-full which contains the sentence info
    :return: dictionary of spans (with indexing of sentences starting at 1 as in protest/parcor)
    """

    sentences_spans = {}

    with open(markables + "/" + doc_id + "_" + "sentence_level.xml", "r", encoding="utf-8") as key:
        soup = BeautifulSoup(key, "xml")
        for m in soup.find_all("markable"):
            span = re.match(r'[a-z]+_([0-9]+)\.\.[a-z]+_([0-9]+)', m['span'])
            sent_id = int(m['orderid'])
            start = int(span.group(1))
            end = int(span.group(2))
            sentences_spans[sent_id] = (start, end)
    return sentences_spans


def treat_span(span_value):
    '''
    :param span_value: m['span'] : span value
    :return: list of positions (starting 1) of tokens to retrieve per markable
    '''

    final = []
    listspans = span_value.split(",")
    lengthspans = len(listspans)
    if lengthspans == 1:# one word or one group of consecutive words
        if ".." not in span_value:# one word ex: "word_1796"
            final.append(int(re.match(r'[a-z]+_([0-9]+)', span_value).group(1)))
        if ".." in span_value:# multiple words ex: word_334..word_335
            position = re.match(r'[a-z]+_([0-9]+)\.\.[a-z]+_([0-9]+)', span_value)
            start = int(position.group(1))
            end = int(position.group(2))
            for i in list(range(start, end+1)):
                final.append(int(i))
    else:  # several words or groups of consecutive words
        for span in listspans:
            if ".." not in span:  # one word ex: "word_1796"
                final.append(int(re.match(r'[a-z]+_([0-9]+)', span).group(1)) - 1)
            if ".." in span:  # multiple words ex: word_334..word_335
                position = re.match(r'[a-z]+_([0-9]+)\.\.[a-z]+_([0-9]+)', span)
                start = int(position.group(1))
                end = int(position.group(2))
                for i in list(range(start, end+1)):
                    final.append(i)
    return final


def get_sent_position(sents_spans, list_of_positions):

    temp = []
    for key in sents_spans:
        span = sents_spans[key]
        indexes = set(list(range(span[0], span[1]+1)))
        for position in list_of_positions:
            if position in indexes:
                temp.append(key)
    return list(set(temp))



def get_chain_info(doc_id, markables):
    """
    gets all coref chains in the document.
    Returns a dictionary with extracted chains with coref_class as key
    """

    info = {}
    with open(markables + "/" + doc_id + "_" + "coref_level.xml", "r", encoding="utf-8") as key:
        soup = BeautifulSoup(key, "xml")
        for m in soup.find_all("markable"):
            coref_class = m["coref_class"]
            #doc_position.sort(key=lambda x: x[0])
            if coref_class in info:
                info[coref_class].append(treat_span(m["span"]))
            else:
                info[coref_class] = [treat_span(m["span"])]
    return info


def get_sentence_level_info(sentences_ids, doc_position):

    for key in sentences_ids:
        span = sentences_ids[key]
        indexes = list(range(span[0], span[1]+1))
        # {0: (1, 16), 1: (17, 32), 2: (33, 62), 3: (63, 77), ...}
        if doc_position in indexes:
            sentence_position = indexes.index(doc_position)
            sentence_id = int(key)
            return (sentence_id, sentence_position)


def read_rawfile(f):
    translations = open(f, "r", encoding="utf=8")
    all = {}
    sent = 0
    for line in translations:
        trans = line.strip('\n').split(" ")
        all[sent] = trans
        sent += 1
    translations.close()
    return all


def get_sent_position(chains_in_doc, sents_in_doc):
    """
    :param chains_in_doc: dict of list of positions
    :param sents_in_doc: dic of tuples indicating start end spans
    :return: {chain_34: {sent2:[[position4, position3], [position23]], ...}...}
    """

    new_chains_info = {}
    for chain in chains_in_doc:
        sentence_info = {}
        for mention in chains_in_doc[chain]:
            temp = []
            for word in mention:
                n_sent, word_position = get_sentence_level_info(sents_in_doc, int(word))
                temp.append(word_position)
            if n_sent in sentence_info:
                sentence_info[n_sent].append(temp)
            else:
                sentence_info[n_sent] = [temp]
        new_chains_info[chain] = sentence_info
    return new_chains_info


def organize_align(alignments):
    """
    alignments -> ['0-0', '1-1', '2-2', '3-3', '4-4', '5-5', '6-5', '8-6', '12-7', '7-8', '9-9', '13-10', '14-11', '15-13']
    out -> {source: [tgt, tgt2, tgt3, ...]...}
    """

    new = {}
    for pair in alignments:
        st = pair.split('-')
        s = int(st[0])
        t = int(st[1])
        if s in new:
            new[s].append(t)
        else:
            new[s] = [t]
    return new


def match_mentions_to_tgt(chains, giza):
    """                       src positions
    # in -> {sent154: {set_268: [[2, 3, 4], [7]]}, sent155: {set_268: [[2]]}}
                                tgt positions
    # out -> {set_238: {154: [[2, 3, 4], [7]], 155: [[2]]}, ...}
    """
    out = {}

    for chain in chains:
        targets = {}
        for sent in chains[chain]:
            tgt_words = []
            align_info = organize_align(giza[sent])
            for mention in chains[chain][sent]:
                positions = []
                for word in mention:
                    if word in align_info:# word may not be aligned
                        positions += align_info[word]
                tgt_words.append(positions)
            targets[sent] = tgt_words
        out[chain] = targets

    return out






def get_chains_position(en_coref_chains):
    """
    :param {set_268 {154: [[2, 3, 4], [7]], 155: [[2]]}, ...}
    :return {sent154: {set_268: [[2, 3, 4], [7]]}, sent155: {set_268: [[2]]}}

    """
    sentences = {}
    chains = {}

    for chain_key in en_coref_chains:
        for sentence in en_coref_chains[chain_key]:
            if sentence in sentences:
                if chain_key in chains:
                    chains[chain_key] += en_coref_chains[chain_key][sentence]
                else:
                    chains[chain_key] = en_coref_chains[chain_key][sentence]
            else:
                sentences[sentence] = chains
                sentences[sentence][chain_key] = en_coref_chains[chain_key][sentence]
                chains = {}
    return sentences







def main():
    if len(sys.argv) != 3:
        sys.stderr.write('Usage: {} {} {} \n'.format(sys.argv[0], "path_to_parcor-full", "alignment_file"))

        '''
        sys.stderr.write('Usage: {} {} {} {} {} \n'.format(sys.argv[0], "path_to_parcor-full", "alignment_file",
                                                           "target_txt_file",
                                                           "output_file"))
                                                           '''
        sys.exit(1)

    endeDocs = ["000_1756_words.xml", "001_1819_words.xml", "002_1825_words.xml", "003_1894_words.xml",
                "005_1938_words.xml", "006_1950_words.xml", "007_1953_words.xml", "009_2043_words.xml",
                "010_205_words.xml", "011_2053_words.xml"]

    base_path = sys.argv[1]
    en_path_all = base_path + "/" + "DiscoMT" + "/" + "EN"
    en_data_dir = en_path_all + "/" + "Basedata"
    en_annotation_dir = en_path_all + "/" + "Markables"

    de_path_all = base_path + "/" + "DiscoMT" + "/" + "DE"
    de_data_dir = de_path_all + "/" + "Basedata"
    de_annotation_dir = de_path_all + "/" + "Markables"

    giza_alignments = read_alignments(sys.argv[2])

    #target_text = read_rawfile(sys.argv[3])
    #out = open(sys.argv[4], "w", encoding = "utf-8")

    for doc in endeDocs: #loop and keep order of protest
        docid = re.findall(r'[0-9]+_[0-9]+', doc)[0]  # returns list therefore the index
        print("Document ==>", docid)

        # document as single list of words
        en_document = create_document(en_data_dir, doc)

        # {0: (1, 16), 1: (17, 32), 2: (33, 62),...}
        en_sentences_ids = make_sentences_spans(docid, en_annotation_dir)
        de_sentences_ids = make_sentences_spans(docid, de_annotation_dir)

        #coref chains

        en_coref_chains = get_chain_info(docid, en_annotation_dir)
        de_coref_chains = get_chain_info(docid, de_annotation_dir)

        print("total of SOURCE chains ==>", len(en_coref_chains))
        print("total of TARGET chains ==>", len(de_coref_chains))

        en_chains_wrt_sent = get_sent_position(en_coref_chains, en_sentences_ids) # 0 based both sentences and indexes
        de_chains_wrt_sent = get_sent_position(de_coref_chains, de_sentences_ids)

        en_sents_wrt_en_chains = get_chains_position(en_chains_wrt_sent)
        de_sents_wrt_de_chains = get_chains_position(de_chains_wrt_sent)

        en_chains_w_target = match_mentions_to_tgt(en_sents_wrt_en_chains, giza_alignments)

        # print("English chains as keys ----->")
        # for key in en_chains_wrt_sent:
        #     print(key, en_chains_wrt_sent[key])
        # print("\n", "\n")

        # print("English sentences as keys ----->")
        # for key in en_sents_wrt_en_chains:
        #     print(key, en_sents_wrt_en_chains[key])
        #
        # print("\n", "\n")
        # print("German ----->")
        # for key in de_sents_wrt_de_chains:
        #     print(key, de_sents_wrt_de_chains[key])




        break




if __name__ == "__main__":
    main()








