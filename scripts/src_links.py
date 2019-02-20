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
    """
    :param f: file from argv
    :return: dict {0: ['0-0', '1-1', ...], 1: ['0-0', "1-1"]...}
    """
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




def organize_align_SRCTGT(alignments):
    """
    alignments -> ['0-0', '1-1', '2-2', '3-3', '4-4', '5-5', '6-5', '8-6', '12-7', '7-8', '9-9', ...]
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


def organize_align_TGTSRC(alignments):
    """
    alignments -> ['0-0', '1-1', '2-2', '3-3', '4-4', '5-5', '6-5', '8-6', '12-7', '7-8', '9-9', '13-10', '14-11', '15-13']
    out -> {target: [src, src2, scr3, ...]...}
    """

    new = {}
    for pair in alignments:
        st = pair.split('-')
        s = int(st[0])
        t = int(st[1])
        if t in new:
            new[t].append(s)
        else:
            new[t] = [s]
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
        align_info = organize_align_SRCTGT(giza[s])#{0: [0], 1: [1], 2: [2], 3: [3], ...}
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

#------------------------------------------------------------------------------------------------------------------------
def scoreChains(enSentenceChains, deSentenceChains, sentenceAlignment):

    '''idea of computing SE*SD scores, scoring SE, SD then take the average and then compare and take max

    chains english: {'set_102': {0: [25], 1: [41], 2: [37], 5: [43], 6: [47]}, 'empty': {4: [32]}, 'set_134': {0: [4]}}

    chains german: {'set_128': {0: [20], 2: [29], 3: [38], 4: [36], 5: [43]}, 'set_124': {0: [2]}}

    sentenceAlig: ['0-0', '0-1', '1-2', '2-3', '8-6', '4-7', '5-8', '6-9', '7-9', '3-10', '9-11', '10-13', ...]

     '''


    alignmentsENDE = organize_align_SRCTGT(sentenceAlignment)
    alignmentsDEEN = organize_align_TGTSRC(sentenceAlignment)

    ALLcombined = {}

    for enChain in enSentenceChains:

        combinations = {}

        for deChain in deSentenceChains:

            de_candidates = []
            en_candidates = []
            scoreEnglish = 0
            scoreGerman = 0
            for de_mention in deSentenceChains[deChain]:

                de_candidates += deSentenceChains[deChain][de_mention]

            for en_mention in enSentenceChains[enChain]:

                en_candidates += enSentenceChains[enChain][en_mention]

            for enWord in en_candidates:
                if enWord in alignmentsENDE: # alignments might be empty
                    for alignPoint in alignmentsENDE[enWord]:
                        if alignPoint in de_candidates:
                            scoreEnglish += 1/len(alignmentsENDE[enWord])

            for deWord in de_candidates:
                if deWord in alignmentsDEEN: # alignments might be empty
                    for alignPoint in alignmentsDEEN[deWord]:
                        if alignPoint in en_candidates:
                            scoreGerman += 1/len(alignmentsDEEN[deWord])

            scoreAVG = (scoreEnglish + scoreGerman) / 2

            combinations[deChain] = scoreAVG

        ALLcombined[enChain] = combinations

    return ALLcombined


def hasDuplicates(scores):

    for each in scores:
        count = scores.count(each)
        if count > 1:
            return True
    return False


def tryFindMax(scores):

    testSet = set(scores)
    i = 9999
    if len(testSet) == 1:
        #"all have the same score"
        i = 9999
    else:
        #TODO: if there are four chains where two have the same socore and two other have the same score too, this is
        # going to be an error
        highestScore = max(scores)
        i = scores.index(highestScore)

    return i


def getHighest(scored):
    """
    :param scored: {'set_3': {'set_2': 1.0, 'set_3': 1.0}, 'set_219': {'set_2': 1.0, 'set_3': 13.0}}
    :return: highgest = {'set_3': "duplicate", 'set_219': 'set_3': 13.0 }
    """
    highest = {}

    for enChain in scored:
        scores = []
        deKeys = []
        for deChain in scored[enChain]:
            deKeys.append(deChain)
            scores.append(scored[enChain][deChain])

        if hasDuplicates(scores):
            i = tryFindMax(scores)
            if i == 9999:
                highest[enChain] = deKeys
            else:
                highest[enChain] = deKeys[i]
        else:
            highestScore = max(scores)
            i = scores.index(highestScore)
            highest[enChain] = deKeys[i]
    return highest



def prettify_chains(mentions, text):

    """
    :param mentions: {1: [9, 10], 2: [3, 4]}
    :param text: string
    :return: mentions: {1: [the arm], 2: [the leg]}
    """

    sentence = text.split()
    prettified = {}


    for mention in mentions:
        pretty_mention = []
        for word in mentions[mention]:
            if word < len(sentence):
                pretty_mention.append(sentence[word])
            else:
                print("indexing error") #"weird case", word, sentence, len(sentence))
        prettified[mention] = " ".join(pretty_mention)
    return prettified


##################################################################################################################


def make_doc_level_align(i, alignments):

    align_this_doc = {}

    ordered_aligns = sorted(alignments.keys())
    this_doc = ordered_aligns[:i]

    counter = 0
    for sent in this_doc:
        align_this_doc[counter] = alignments[sent]
        del alignments[sent]
        counter += 1
    return align_this_doc


def transform_aligns(document_aligns):

    transformed = {}
    ordered_keys = sorted(document_aligns.keys())
    for key in ordered_keys:
        new_aligns = []
        if key == 0:
            transformed[key] = document_aligns[key]
        else:
            for s_t in document_aligns[key]:
                each = s_t.split("-")
                en = int(each[0])
                de = int(each[1])
                last_one = transformed[key-1][-1].split("-")
                new_en = int(last_one[0]) + 1 + en
                new_de = int(last_one[1]) + 1 + de
                new_pair = str(new_en) + "-" + str(new_de)
                new_aligns.append(new_pair)
            transformed[key] = new_aligns
    return transformed


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

        len_en = len(en_sentences_ids.keys())

        #make alignments document level
        doc_aligns = make_doc_level_align(len_en, giza_alignments)
        reindexed_doc_alings = transform_aligns(doc_aligns)

        #coref chains

        en_coref_chains = get_chain_info(docid, en_annotation_dir)
        de_coref_chains = get_chain_info(docid, de_annotation_dir)

        #print(en_coref_chains)

        print_stats(en_path_all, doc, en_coref_chains, de_coref_chains)

        #en_chains_in_sentence = transform_chains_into_sentences(en_coref_chains, en_sentences_ids)
        #de_chains_in_sentence = transform_chains_into_sentences(de_coref_chains, de_sentences_ids)

        #align_of_en_chains = match_mentions_to_tgt(en_chains_in_sentence, giza_alignments)

        #print("giza_alignments", giza_alignments)
        print("doc_aligns", doc_aligns)
        print("\n")
        print("reindexed_doc_alings", reindexed_doc_alings)
        print("\n")
        print("words in en_document", len(en_document))
        print("\n")
        print("en_sentences_ids", en_sentences_ids)
        #print("\n")
        #print("en_coref_chains", en_coref_chains)

        # for i in range(len(sentence_based_enDoc)):
        #     enSentence = sentence_based_enDoc[i]
        #     if i >= len(sentence_based_deDoc):
        #         print("==>problem with sentence splitting annotation in this document")
        #         deSentence = sentence_based_deDoc[i-1]
        #     else:
        #         deSentence = sentence_based_deDoc[i]
        #
        #     print(enSentence)
        #     print(deSentence)
        #     print("\n")
        #
        #     if i in en_chains_in_sentence:
        #         if i in de_chains_in_sentence:
        #             #print("==>MATCHING CHAINS")
        #             #print("\n")
        #
        #             #print("chains english:", en_chains_in_sentence[i])
        #             #print("chains german:", de_chains_in_sentence[i])
        #             #print("chains alined:", align_of_en_chains[i])
        #
        #             correspondancesScores = scoreChains(en_chains_in_sentence[i], de_chains_in_sentence[i], giza_alignments[i])
        #             ChainPairs = getHighest(correspondancesScores)
        #
        #             for enChain in ChainPairs:
        #                 deChain = ChainPairs[enChain]
        #
        #                 if type(deChain) is str:
        #                     print("CHAIN MATCH")
        #                     print("ENchain:", enChain, "corresponds to DEchain", deChain)
        #                     new = prettify_chains(en_chains_in_sentence[i][enChain], sentence_based_enDoc[i])
        #                     print("ENchain", enChain, "with mentions:", new)
        #                     print("DEmentions")
        #                     new = prettify_chains(de_chains_in_sentence[i][deChain], sentence_based_deDoc[i])
        #                     print("DEchain", deChain, "with mentions:", new)
        #                     print("\n")
        #
        #                 else:
        #                     print("OVERLAP")
        #                     print("Mentions in ENchain:", enChain, "found in these DEchains", deChain)
        #                     print("ENmentions")
        #                     new = prettify_chains(en_chains_in_sentence[i][enChain], sentence_based_enDoc[i])
        #                     print("ENchain", enChain, "with mentions:", new)
        #                     for mention in de_chains_in_sentence[i]:
        #                         new = prettify_chains(de_chains_in_sentence[i][mention], sentence_based_deDoc[i])
        #                         print("DEchain:", mention, "with mentions:", new)
        #                     print("\n")
        #
        #
        #             # # TODO: german chains not in english in sentence that is annotated in both
        #             # # ex: And a lot of the time the question
        #             # TODO: not sure is relevant because Im printing everything already
        #             # for key in de_chains_in_sentence[i]:
        #             #     if key not in ChainPairs.values():
        #             #         print("==>GermanChainsNotInEnglish!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        #             #         print("chains german:", key, "with mentions", de_chains_in_sentence[i][key])
        #             #         print("\n")
        #
        #         else:
        #             print("==>EnglishChainsNotInGerman")
        #
        #             for chain in en_chains_in_sentence[i]:
        #                 new = prettify_chains(en_chains_in_sentence[i][chain], sentence_based_enDoc[i])
        #                 print("ENchain:", mention, "with mentions:", new)
        #             print("\n")
        #     else:
        #
        #         if i in de_chains_in_sentence:
        #             print("==>GermanChainsNotInEnglish")
        #             for mention in de_chains_in_sentence[i]:
        #                 new = prettify_chains(de_chains_in_sentence[i][mention], sentence_based_deDoc[i])
        #                 print("DEchain:", mention, "with mentions:", new)
        #                 print("\n")
        #
        #         else:
        #             print("==>Unannotated sentence pair")
        #             print("\n")




if __name__ == "__main__":
    main()



