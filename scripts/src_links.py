#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extracts links from parcor-full

!!!!!NOTE: in parcorfull numbering for sentences starts at 0 but numbering for words starts at 1
"""

import sys, re
import collections
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
            if span:
                sent_id = int(m['orderid'])
                start = int(span.group(1))
                end = int(span.group(2))
                sentences_spans[sent_id] = (start, end)
    return sentences_spans



def make_sentence_based_doc(document, sentences_ids):
    # {0: (1, 16), 1: (17, 32), 2: (33, 62),...}
    new = []
    for key in sorted(sentences_ids):
        temp = []
        span = sentences_ids[key]
        for i in range(span[0]-1, span[1]):
            temp.append(document[i])
        new.append(" ".join(temp))
    return new



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


def transform_chains_into_sentences2(chains_in_doc, sentences_in_doc):
    """
    :param chains_in_doc: dict of list of positions {set_279: [[185, 186], [160, 161], [146, 147]],...}
    :param sentences_in_doc: dic of tuples indicating start end spans {0: (1, 16), 1: (17, 32), 2: (33, 62),...}
    :return: {sent154: {set_268: [[2, 3, 4], [7]]}, sent155: {set_268: [[2]]}}
    """
    out_sentences = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
    # {sent_154: {set_268: {ment_2: [2, 3, 4]}}}

    for chain in chains_in_doc:

        for mention_id, mention in enumerate(chains_in_doc[chain]):
            # mention can span multiple sentences
            for word in mention:
                sentenceID, position = get_sentence_level_info(sentences_in_doc, word)
                out_sentences["sent_" + str(sentenceID)][chain]["ment_" + str(mention_id)].append(position)

    return out_sentences


def transform_chains_into_sentences(chains_in_doc, sentences_in_doc):
    """
    :param chains_in_doc: dict of list of positions {set_279: [[185, 186], [160, 161], [146, 147]],...}
    :param sentences_in_doc: dic of tuples indicating start end spans {0: (1, 16), 1: (17, 32), 2: (33, 62),...}
    :return: {sent154: {set_268: [[2, 3, 4], [7]]}, sent155: {set_268: [[2]]}}
    """
    out_sentences = {}
    # {sent_154: {set_268: {ment_2: [2, 3, 4]}}}

    for chain in chains_in_doc:

        for mention_id, mention in enumerate(chains_in_doc[chain]):
            # mention can span multiple sentences
            for word in mention:
                sentenceID, position = get_sentence_level_info(sentences_in_doc, word)
                #sentstr = "sent_" + str(sentenceID)
                #mentstr = "ment_" + str(mention_id)
                if sentenceID not in out_sentences:
                    out_sentences[sentenceID] = {}
                if chain not in out_sentences[sentenceID]:
                    out_sentences[sentenceID][chain] = {}
                if mention_id not in out_sentences[sentenceID][chain]:
                    out_sentences[sentenceID][chain][mention_id] = []
                out_sentences[sentenceID][chain][mention_id].append(position)

    return out_sentences




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


def match_mentions_to_tgt(sentences, giza):

    """                         src positions
    # in -> {1134 {'set_288': {1: [19], 2: [29], 8: [13]}, 'set_289': {2: [2]}}
                                tgt positions
    # out -> {154 {'set_268': {0: [2, 3, 4], 2: [7]}}...}
    """
    out = {}

    for s in sentences:
        targets = {}
        align_info = organize_align(giza[s])#{0: [0], 1: [1], 2: [2], 3: [3], ...}
        for chain in sentences[s]:
            tgt_words = {}
            for mention in sentences[s][chain]:
                positions = []
                for word in sentences[s][chain][mention]:
                    if word in align_info:# word may not be aligned
                        positions += align_info[word]
                tgt_words[mention] = list(set(positions))
            targets[chain] = tgt_words
        out[s] = targets
    return out


def find_partial(mentions, chains):
    # [[0, 1], [0, 1], [11]]
    # {'set_271': [[3], [16, 17], [4, 5]]}

    for mention in mentions:
        for word in mention:
            for chain in chains:
                for mention_b in chains[chain]:
                    if word in mention_b:
                        return True
    return False





def print_stats(en_path_all, doc, en_coref_chains, de_coref_chains):
    # (PRINT some statistics
    en_mention_count = 0
    de_mention_count = 0

    en_word_count = 0
    de_word_count = 0
    print("****************************************")
    print("STATISTICS PER DOC")
    print("Document ==> ", en_path_all + doc)
    for key in en_coref_chains:
        en_mention_count += len(en_coref_chains[key])
        for mention in en_coref_chains[key]:
            en_word_count += len(mention)
    for key in de_coref_chains:
        de_mention_count += len(de_coref_chains[key])
        for mention in de_coref_chains[key]:
            de_word_count += len(mention)

    print("SOURCE chains: ", len(en_coref_chains))
    print("SOURCE mentions: ", en_mention_count)
    print("SOURCE annotated words: ", en_word_count)
    print("TARGET chains: ", len(de_coref_chains))
    print("TARGET mentions: ", de_mention_count)
    print("TARGET annotated words: ", de_word_count)
    print("****************************************")
    print("\n")
    # )

def put_into_words(relevant, sentence):
    # [[0], [4, 5]]

    s = sentence.split()
    final = []
    for mention in relevant:
        temp = []
        for word in mention:
            if word < len(s):
                temp.append(s[word])
        new_mention = " ".join(temp)
        final.append(new_mention)
    return final


    ####################################################################################################################################################################


def ChainStatus(enChains, deChains):

    if len(enChains) == len(deChains):
        print('=> Same number of chains in english and german')
        return "equal"

    elif len(enChains) > len(deChains):
        print('=> More chains in english than german')
        return "enlonger"
    else:
        print('=> More chains in german than english')
        return "gelonger"


def scoreChains(enSentenceChains, deSentenceChains, sentenceAlignment):

    '''idea of computing SE*SD scores, scoring SE, SD then take the average and then compare and take max

    chains english: {'set_102': {0: [25], 1: [41], 2: [37], 5: [43], 6: [47]}, 'empty': {4: [32]}, 'set_134': {0: [4]}}

    chains german: {'set_128': {0: [20], 2: [29], 3: [38], 4: [36], 5: [43]}, 'set_124': {0: [2]}}

    chains alined: {'set_102': {0: [24], 1: [40], 2: [36], 5: [40], 6: []}, 'empty': {4: [31]}, 'set_134': {0: [4]}}

     '''
    enWords = []

    for enChain in enSentenceChains:











# #def matchChainsInSentence(enChains, deChains, align):
#
#     """
#     chains english sent 23: {11: [6], 13: [29], 26: [0], 28: [18]}}
#     chains german sent 23:  {12: [16], 13: [25], 14: [2], 16: [6], 19: [31]}, 'set_87': {0: [9], 1: [3, 4, 5, 6, 7]},...}
#     chains alined sent 23:  {11: [6], 13: [31], 26: [0], 28: [16]}}
#     enChains[chain]-------> {0: [8, 9], 1: [10, 11], 2: [25], 3: [13, 14, 15, 16, 17, 18]}
#     deChains[chain]-------> {0: [4], 1: [1, 2]}
#     alChains[chain]-------> {0: [25, 26, 27]}
#
#     """
#
#     #status = ChainStatus(enChains, deChains)
#
#     # if status == "equal":
#     #
#     # for chain in deChains:
#     #     for mention in deChains[chain]:
#     #         # loop through all alignments
#     #         for alChain in align:
#     #             for alMention in align[alChain]:
#     #                 if mention == alMention:
#     #                     return chain
#     #
#     # return deChain, alignChain
#
#
#     # elif status == "enlonger":
#     #
#     #
#     # else:
#     #




def main():
    if len(sys.argv) != 3:
        sys.stderr.write('Usage: {} {} {} \n'.format(sys.argv[0], "path_to_parcor-full", "alignment_file"))

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


    for doc in endeDocs: #loop and keep order of protest
        docid = re.findall(r'[0-9]+_[0-9]+', doc)[0]  # returns list therefore the index

        # document as single list of words
        en_document = create_document(en_data_dir, doc)
        de_document = create_document(de_data_dir, doc)

        en_sentences_ids = make_sentences_spans(docid, en_annotation_dir)
        de_sentences_ids = make_sentences_spans(docid, de_annotation_dir)

        sentence_based_enDoc = make_sentence_based_doc(en_document, en_sentences_ids)
        sentence_based_deDoc = make_sentence_based_doc(de_document, de_sentences_ids)

        #coref chains

        en_coref_chains = get_chain_info(docid, en_annotation_dir)
        de_coref_chains = get_chain_info(docid, de_annotation_dir)

        #print(en_coref_chains)

        print_stats(en_path_all, doc, en_coref_chains, de_coref_chains)

        en_chains_in_sentence = transform_chains_into_sentences(en_coref_chains, en_sentences_ids)
        de_chains_in_sentence = transform_chains_into_sentences(de_coref_chains, de_sentences_ids)

        align_of_en_chains = match_mentions_to_tgt(en_chains_in_sentence, giza_alignments)

        for i in range(len(sentence_based_enDoc)):
            enSentence = sentence_based_enDoc[i]
            if i >= len(sentence_based_deDoc):
                print("problem with sentence splitting annotation in this document")
                deSentence = sentence_based_deDoc[i-1]
            else:
                deSentence = sentence_based_deDoc[i]

            print(enSentence)
            print(deSentence)

            if i in en_chains_in_sentence:

                if i in de_chains_in_sentence:
                    print("==>TODO:matching")
                    #matchChainsInSentence(en_chains_in_sentence[i], de_chains_in_sentence[i], align_of_en_chains[i])

                    correspondances = scoreChains(en_chains_in_sentence[i], de_chains_in_sentence[i], giza_alignments[i])
                    print("chains english:", en_chains_in_sentence[i])
                    print("chains german:", de_chains_in_sentence[i])
                    print("chains alined:", align_of_en_chains[i])
                    print("\n")

                else:
                    print("==>EnglishChainsNotInGerman")
                    print(en_chains_in_sentence[i])

            else:
                if i in de_chains_in_sentence:
                    print("==>GermanChainsNotInEnglish")
                    print("chains german:", de_chains_in_sentence[i])
                    print("\n")
                else:
                    print("==>Unannotated sentence pair")
                    print("\n")




if __name__ == "__main__":
    main()



