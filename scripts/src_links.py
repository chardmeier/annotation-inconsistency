#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# /usr/bin/env python3
# -*- encoding: utf-8 -*-

"""
Extracts links from parcor-full

!!!!!NOTE: in parcorfull numbering for sentences starts at 0 but numbering for words starts at 1
"""

import sys, re
from bs4 import BeautifulSoup


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
    :return: list of positions of tokens to retrieve per markable
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



def get_pro_info(doc_id, markables, coref_chains):
    '''
    gets all pronouns of interest in the document.
    Returns a dictionary with extracted prons with sent_id as key
    '''

    info = []
    with open(markables + "/" + doc_id + "_" + "coref_level.xml", "r", encoding="utf-8") as key:
        soup = BeautifulSoup(key, "xml")
        for m in soup.find_all("markable"):
            # pronouns
            if ('mention' in m.attrs) and (m['mention'] == "pronoun"):
                # then type
                pron_type = m["type"]
                doc_position = treat_span(m["span"])# position is now a list
                antetype = m["antetype"] if "antetype" in m.attrs else "no_antetype"
                agreement = m["agreement"] if "agreement" in m.attrs else "none"
                pro_position = m["position"] if "position" in m.attrs else "none"
                coref_class = m["coref_class"] if "coref_class" in m.attrs else "empty"
                if coref_class in coref_chains:
                    chain = coref_chains[coref_class]
                    chain.sort(key=lambda x: x[0], reverse=True)
                else:
                    chain = []
                info.append((pron_type, doc_position, antetype, agreement, pro_position, coref_class, chain))
    return info


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


def make_sentences(whole_doc, sentences_ids):
    '''converts whole_doc from a list of words to a list of sentences
    according to sentences_ids which is a dictioary'''

    new_doc = []
    for key in sentences_ids:
        span = sentences_ids[key]
        sentence = []
        indexes = list(range(span[0], span[1] + 1))
        for i in indexes:
            sentence.append(whole_doc[i-1])
        text_sentence = " ".join(sentence)
        new_doc.append(text_sentence)
    return new_doc


def read_alignments(f):
    #import sys
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


def get_tgt_positions(dict_of_align, sentence_num, src_position):
    targets = []
    if sentence_num in dict_of_align:
        for s_t in dict_of_align[sentence_num]:
            st = s_t.split('-')
            s = int(st[0])
            t = int(st[1])
            if s == src_position:
                targets.append(t)
    return targets


def get_tgt_words(tgt_positions, sentence_num, target_text):
    targets = []
    for position in tgt_positions:
        if position < len(target_text):
            targets.append(target_text[sentence_num][position])
    return targets


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


def format_line(sent_num, info_per_sentence_with_tgt, sentence):
    #                                                                0                                      1       2
    # info_per_sentence_with_tgt --> [(('000_1756', 'speaker reference', 249, 'my', 'no_antetype', 14, 5), [6], ['meine']),...] "

    #         0         1         2           3       4         5             6
    # 0 -> (docid, type_pron, doc_position, pron, antetype, sentence_id, sentence_position)

    # trans_info --> ([4], [b'das'])

    temp_types = []
    temp_src_positions = []
    temp_prons = []
    temp_antetypes = []
    temp_agreements = []
    temp_pro_positions = []
    temp_antecedents = []
    temp_heads = []
    temp_tgt_words = []
    temp_tgt_positions = []
    temp_inter_intra = []
    temp_ant_spans = []

    # (pron_type, doc_position, antetype, agreement, pro_position, coref_class)

    if sent_num in info_per_sentence_with_tgt:
        for each in info_per_sentence_with_tgt[sent_num]:
            src_info = each[0]
            tgt_pos = each[1]
            tgt_words = each[2]
            temp_types.append(src_info[1])
            temp_src_positions.append(src_info[6])
            temp_prons.append(src_info[3])
            temp_antetypes.append(src_info[4])
            temp_agreements.append(src_info[7])
            temp_pro_positions.append(src_info[8])
            temp_antecedents.append(src_info[10])
            temp_heads.append(src_info[11])
            temp_inter_intra.append(src_info[14])
            temp_tgt_words.append(" ".join(tgt_words))
            temp_tgt_positions.append(" ".join([str(i) for i in tgt_pos]))
            temp_ant_spans.append(src_info[15])
        new = ["|||".join(temp_types), "|||".join([str(i) for i in temp_src_positions]), "|||".join(temp_prons),
               "|||".join(temp_antetypes), "|||".join(temp_agreements), "|||".join(temp_pro_positions),
               "|||".join(temp_antecedents), "|||".join(temp_heads), "|||".join(temp_inter_intra),
               "|||".join(temp_tgt_words), "|||".join(temp_tgt_positions), "|||".join(temp_ant_spans), sentence]
        new_string = "\t".join(new)
        return new_string + "\n"
    else:
        new = ["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", sentence]
        new_string = "\t".join(new)
        return new_string + "\n"


def get_nearest_ant(pro_pos, chain):
    for element in chain:
        ant_found = []
        for span in element:
            if span[0] < pro_pos:
                ant_found.append(True)
            else:
                ant_found.append(False)
        if list(set(ant_found)) == [True]:
            return element
    return []


def main():
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: {} {} \n'.format(sys.argv[0], "path_to_parcor-full"))

        '''
        sys.stderr.write('Usage: {} {} {} {} {} \n'.format(sys.argv[0], "path_to_parcor-full", "alignment_file",
                                                           "target_txt_file",
                                                           "output_file"))
                                                           '''
        sys.exit(1)

    endeDocs = ["000_1756_words.xml", "001_1819_words.xml", "002_1825_words.xml", "003_1894_words.xml", "005_1938_words.xml", "006_1950_words.xml", "007_1953_words.xml", "009_2043_words.xml", "010_205_words.xml", "011_2053_words.xml"]

    incdocsentcounts = {'000_1756': 0,
                        '001_1819': 186,
                        '002_1825': 335,
                        '003_1894': 457,
                        '005_1938': 690,
                        '006_1950': 792,
                        '007_1953': 1034,
                        '009_2043': 1268,
                        '010_205': 1420,
                        '011_2053': 1610}

    current_path = sys.argv[1]
    path_all = current_path + "/" + "DiscoMT" + "/" + "EN"
    data_dir = path_all + "/" + "Basedata"
    annotationfiles_dir = path_all + "/" + "Markables"

    #giza_alignments = read_alignments(sys.argv[2])
    #target_text = read_rawfile(sys.argv[3])
    #out = open(sys.argv[4], "w", encoding = "utf-8")

    temp_sentences = 0

    for doc in endeDocs: #loop and keep order of protest
        print(doc, "===>")
        document = []  # document as single list of words
        info_per_sentence = {}
        docid = re.findall(r'[0-9]+_[0-9]+', doc)[0]  # returns list therefore the index
        shortdocid = int(re.findall(r'[0-9]+', doc)[1])
        with open(data_dir + "/" + doc, "r", encoding="utf-8") as xmldoc:
            soup = BeautifulSoup(xmldoc, "xml")
            # make doc out of _words.xml files
            for w in soup.find_all("word"):
                document.append(w.string)

            sentences_ids = make_sentences_spans(docid, annotationfiles_dir) # {0: (1, 16), 1: (17, 32), 2: (33, 62),...}

            sentences_in_doc = make_sentences(document, sentences_ids)

            coref_chains = get_chain_info(docid, annotationfiles_dir)

            print(coref_chains)
            print("\n", "\n")

#             info = get_pro_info(docid, annotationfiles_dir, coref_chains)  # info in one document
#
#             for each in info:
#                 type_pron = each[0]
#                 doc_position = each[1][0]
#                 pron = document[doc_position-1]
#                 antetype = each[2]
#                 agreement = each[3]
#                 pro_position = each[4]
#                 coref_class = each[5]
#                 coref_chain = each[6]
#                 ant_list = []
#                 ant_span_list = []
#                 head_list = []
#                 head_pos_list = []
#                 pro_sentence_id, pro_sentence_position = get_sentence_level_info(sentences_ids, doc_position)
#                 # Antecedents
#                 if coref_chain != []:
#                     antecedent = get_nearest_ant(doc_position,coref_chain)
#                 else:
#                     antecedent = []
#                 for ant in antecedent:
#                     ant_start_sentence_id, ant_start_sentence_position = get_sentence_level_info(sentences_ids, ant[0])
#                     ant_start_sentence_id += incdocsentcounts[docid]
#                     ant_end_sentence_id, ant_end_sentence_position = get_sentence_level_info(sentences_ids, ant[-1])
#                     ant_end_sentence_id += incdocsentcounts[docid]
#                     ant_span = str(ant_start_sentence_id)+':'+str(ant_start_sentence_position)+'-'+str(ant_end_sentence_id)+':'+str(ant_end_sentence_position)
#                     ant_span_list.append(ant_span)
#                     ant_list.append(" ".join([document[a-1] for a in ant]))
#                     head_list.append(document[ant[-1]-1])
#                     head_pos_list.append(ant[-1])
#                 ant_spans = ";".join(ant_span_list)
#                 antecedent = ";".join(ant_list)
#                 head = ";".join(head_list)
#                 ant_sent_info = []
#                 # Antecedent heads
#                 for head_pos in head_pos_list:
#                     ant_sentence_id, ant_sentence_position = get_sentence_level_info(sentences_ids, head_pos)
#                     ant_sent_info.append((ant_sentence_id, ant_sentence_position))
#                 # Determine if pronoun is inter/intra-sentential
#                 if ant_sent_info == []:
#                     inter_intra = "none"
#                 else:
#                     inter_intra = "intra"
#                     ant_sent_ids = list(set(x[0] for x in ant_sent_info))
#                     for aid in ant_sent_ids:
#                         if aid < pro_sentence_id:
#                             inter_intra = "inter"
#                 # Combine information
#                 if pro_sentence_id in info_per_sentence:
#                     info_per_sentence[pro_sentence_id].append((docid, type_pron, doc_position, pron, antetype, pro_sentence_id, pro_sentence_position, agreement, pro_position, coref_class, antecedent, head, head_pos_list, ant_sent_info, inter_intra, ant_spans))
#                 else:
#                     info_per_sentence[pro_sentence_id] = [(docid, type_pron, doc_position, pron, antetype, pro_sentence_id, pro_sentence_position, agreement, pro_position, coref_class, antecedent, head, head_pos_list, ant_sent_info, inter_intra, ant_spans)]
#             xmldoc.close()
#
#             # looping through the whole doc again  -- get translations
#             info_per_sentence_with_tgt = {}
#
#             for i in range(len(sentences_in_doc)):
#                 # print("============>", temp_sentences)
#                 if i in info_per_sentence:
#                     for element in info_per_sentence[i]:
#                         pro_pos = element[6]
#                         pron = element[3]
#                         ant_pos_list = element[13]
#                         if pron.lower() in ["it", "they"]:
#
# ''
#
#                             # get translations of pronoun
#                             tgt_pro_positions = get_tgt_positions(giza_alignments, temp_sentences, pro_pos)
#                             tgt_pro_words = get_tgt_words(tgt_pro_positions, temp_sentences, target_text)
#                             # get translations of antecendent head
#                             if i in info_per_sentence_with_tgt:
#                                 info_per_sentence_with_tgt[i].append((element, tgt_pro_positions, tgt_pro_words))
#                             else:
#                                 info_per_sentence_with_tgt[i] = [(element, tgt_pro_positions, tgt_pro_words)]
#                 temp_sentences += 1
#
#             # looping through the whole doc again  -- format
#             for i in range(len(sentences_in_doc)):
#                 new = format_line(i, info_per_sentence_with_tgt, sentences_in_doc[i])
#                 out.write(new)
#
#     out.close()


if __name__ == "__main__":
    main()








