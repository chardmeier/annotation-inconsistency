#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extracts links from parcor-full

!!!!!NOTE: in parcorfull numbering for sentences starts at 0 but numbering for words starts at 1
"""

import sys, re
from bs4 import BeautifulSoup
import copy

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
            else:
                word = re.match(r'[a-z]+_([0-9]+)', m['span'])
                sent_id = int(m['orderid'])
                start = int(word.group(1))
                end = start + 1
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


def get_chain_info(doc_id, markables):
    """
    gets all coref chains in the document.
    Returns a dictionary with extracted chains with coref_class as key
    """

    info = {}
    chains = {}
    with open(markables + "/" + doc_id + "_" + "coref_level.xml", "r", encoding="utf-8") as key:
        soup = BeautifulSoup(key, "xml")
        for m in soup.find_all("markable"):
            coref_class = m["coref_class"] # 'empty, or a chain number
            markable_type = m["mention"] # pronoun, np, clause, vp

            pron_type, np_type = None, None
            if markable_type == "pronoun":
                if m.has_attr('type_of_pronoun'): # weird inconsistency in annotation tags
                    pron_type = m["type_of_pronoun"]
            if markable_type == "np":
                np_type = m["nptype"]
            # add chain span to chains dict
            if coref_class in chains:
                chains[coref_class].append(treat_span(m["span"]))
                # add annotation info to info dict
                if pron_type:
                    info[coref_class].append((markable_type, pron_type))
                elif np_type:
                    info[coref_class].append((markable_type, np_type))
                else:
                    info[coref_class].append((markable_type, markable_type))
            else:
                chains[coref_class] = [treat_span(m["span"])]
                # add annotation info to info dict
                if pron_type:
                    info[coref_class] = [(markable_type, pron_type)]
                elif np_type:
                    info[coref_class] = [(markable_type, np_type)]
                else:
                    info[coref_class] = [(markable_type, markable_type)]
    return chains, info


def filter_chains(dict_chains, dict_info):

    filtered = copy.deepcopy(dict_chains)
    for chain in dict_info:
        #emtpys are chains not types
        if chain == "empty":
            if chain in filtered:
                del filtered[chain]
        else:
            for mention in dict_info[chain]:
                m_type = mention[0]
                if m_type in ["vp", "clause", None, "empty"]:
                    if chain in filtered:
                        del filtered[chain]
    return filtered


def organize_align_src2tgts(alignments):
    """
    alignments -> reindexed_doc_aligns {0: ['0-0', '1-1', ...], 1: ['35-32', '36-33', ...] ...}
    out -> {target: [src, src2, scr3, ...]...}
    """

    new = {}
    for sentence in alignments:
        for pair in alignments[sentence]:
            st = pair.split('-')
            s = int(st[0])
            t = int(st[1])
            if s in new:
                new[s].append(t)
            else:
                new[s] = [t]
    return new

def organize_align_tgt2srcs(alignments):
    """
    alignments -> reindexed_doc_aligns {0: ['0-0', '1-1', ...], 1: ['35-32', '36-33', ...] ...}
    out -> {target: [src, src2, scr3, ...]...}
    """

    new = {}
    for sentence in alignments:
        for pair in alignments[sentence]:
            st = pair.split('-')
            s = int(st[0])
            t = int(st[1])
            if t in new:
                new[t].append(s)
            else:
                new[t] = [s]
    return new


def match_mentions_to_tgt(en_chains, doc_alignments):
    """
    in ->
    en_chains {'set_291': [[2151], [2083], [2094], [2113]], 'set_255': [[2294, 2295]], 'set_208': [[3911]], 'set_5': [[178, 179]], ...}
    reindexed_doc_aligns {0: ['0-0', '1-1', '2-2', ...], 2: ['32-34', '33-35', ...], ...}

    # out ->
    """
    out = {}

    source2targets = organize_align_src2tgts(doc_alignments)

    for chain in en_chains:
        aligned_mentions = []
        for mention in en_chains[chain]:
            aligned_words = []
            for word_i in mention:
                if word_i in source2targets:
                    aligned_words += list(set(source2targets[word_i]))
            aligned_mentions.append(aligned_words)
        if chain in out:
            out[chain].append(aligned_mentions)
        else:
            out[chain] = aligned_mentions
    return out


def print_stats(en_path_all, doc, en_coref_chains, de_coref_chains, en_filtered, de_filtered):
    # PRINT some basic statistics
    en_mention_count, de_mention_count = 0, 0
    en_word_count, de_word_count = 0, 0
    en_filter_mention, de_filter_mention = 0, 0
    en_filter_words, de_filter_words = 0, 0

    print("****************************************")
    print("STATISTICS PER DOC")
    print(en_path_all + doc)
    for key in en_coref_chains:
        en_mention_count += len(en_coref_chains[key])
        for mention in en_coref_chains[key]:
            en_word_count += len(mention)
    for key in de_coref_chains:
        de_mention_count += len(de_coref_chains[key])
        for mention in de_coref_chains[key]:
            de_word_count += len(mention)


    for key in en_filtered:
        en_filter_mention += len(en_coref_chains[key])
        for mention in en_filtered[key]:
            en_filter_words += len(mention)
    for key in de_filtered:
        de_filter_mention += len(de_filtered[key])
        for mention in de_filtered[key]:
            de_filter_words += len(mention)

    print("src chains:", len(en_coref_chains), "nominal:", len(en_filtered))
    print("src mentions:", en_mention_count, "nominal:", en_filter_mention)
    print("src annotated words:", en_word_count, "nominal:", en_filter_words)
    print("tgt chains:", len(de_coref_chains), "nominal:", len(de_filtered))
    print("tgt mentions:", de_mention_count, "nominal:", de_filter_mention)
    print("tgt annotated words:", de_word_count, "nominal:", de_filter_words)

    print("****************************************")
    print("\n")
    # )


def scoreChains(enChains, deChains, alignments):

    alignmentsENDE = organize_align_src2tgts(alignments)
    alignmentsDEEN = organize_align_tgt2srcs(alignments)

    ALLcombined = {}

    for enChain in enChains:
        combinations = {}
        # TODO: see line 590, some docs are completely without chains after filtering
        if deChains == {}:
            continue
        else:
            for deChain in deChains:

                de_candidates = []
                en_candidates = []

                scoreEnglish = 0
                scoreGerman = 0
                #group all mentions of a chain
                for de_mention in deChains[deChain]:
                    de_candidates += de_mention
                for en_mention in enChains[enChain]:
                    en_candidates += en_mention

                #look for alignment points
                for enWord in en_candidates:
                    reset_i = enWord-1
                    if reset_i in alignmentsENDE: # alignments might be empty
                        for alignPoint in alignmentsENDE[reset_i]:
                            if alignPoint in de_candidates:
                                scoreEnglish += 1

                for deWord in de_candidates:
                    reset_i = deWord-1
                    if reset_i in alignmentsDEEN: # alignments might be empty
                        for alignPoint in alignmentsDEEN[reset_i]:
                            if alignPoint in en_candidates:
                                scoreGerman += 1

                scoreAVG = (scoreEnglish + scoreGerman) / 2
                combinations[deChain] = scoreAVG
        ALLcombined[enChain] = combinations

    #print("All combined========>")
    #print(ALLcombined.keys())
    #print(ALLcombined.values())
    return ALLcombined


def hasDuplicates(scores):

    temp = list(set(scores))
    for each in temp:
        count = temp.count(each)
        if count > 1:
            return True
    return False


def findDuplicates(scores):

    all = {}
    for each in scores:
        all[each] = scores.count(each)
    return all




def getHighest(scored):
    """
    :param scored: {'set_3': {'set_2': 1.0, 'set_3': 1.0}, 'set_219': {'set_2': 1.0, 'set_3': 13.0}}
    :return: highest = {'set_3': "duplicate", 'set_219': 'set_3': 13.0 }
    """
    highest = {}


    # TODO : it seems there are no ties in scores in the DiscoMT data...not sure in other parts of parcorfull
    for enChain in scored:
        scores = []
        deKeys = []
        #loog again to ensure order
        for dekey in scored[enChain]:
            deKeys.append(dekey)
            scores.append(scored[enChain][dekey])

        #print("checking ==>")
        #print(enChain, scores)
        #todo: two english chains can be matched with a same german chain
        if not hasDuplicates(scores):
            highestScore = max(scores)
            i = scores.index(highestScore)
            highest[enChain] = deKeys[i]
        else:
            # two chains with the same score
            duplex = findDuplicates(scores)

    return highest


def order_mention_types(mentions, info):

    ordered_mentions = sorted(mentions)
    ordered_info = []
    for mention in ordered_mentions:
        i = mentions.index(mention)
        ordered_info.append(info[i])
    return ordered_mentions, ordered_info


def prettify_chains(mentions, text, info):

    """
    :param mentions: list of int [[3600, 3601, 3602], [3619], [3605]]
    :param text: list of str
    :param info: [('np', 'antecedent'), ('pronoun', 'personal'), ('pronoun', 'relative')]
    :return: mentions: list of string
    """

    # sort everybody
    ordered_mentions, ordered_info = order_mention_types(mentions, info)

    # prettify
    prettified = []
    formatted_info = []
    for j in range(len(ordered_mentions)):
        pretty_mention = []
        ordered_interior = sorted(ordered_mentions[j])
        for word in ordered_interior:
            pretty_mention.append(text[word-1])
        formatted_info.append("-".join(list(ordered_info[j])))
        prettified.append(" ".join(pretty_mention))

    return (prettified, formatted_info)


    # [('np', 'antecedent'), ('pronoun', 'personal'), ('pronoun', 'relative')]


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


def transform_aligns(en_sents, de_sents, document_aligns):

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
                en_last_one = en_sents[key-1][-1]
                de_last_one = de_sents[key-1][-1]
                new_en = en_last_one + en
                new_de = de_last_one + de
                new_pair = str(new_en) + "-" + str(new_de)
                new_aligns.append(new_pair)
            transformed[key] = new_aligns
    return transformed


def classifyMatches(en_coref_chains, de_coref_chains, matching_chains):

    complete_matches = {}
    partial_matches ={}
    en_not_de = {}
    de_not_en = {}

    #temp = []

    #print("entering en===>", len(en_coref_chains))
    #print("entering de===>", len(de_coref_chains))

    matched_germanchains = list(matching_chains.values())
    #print("matched_germanchains")
    #print(matched_germanchains)

    for chainEn in en_coref_chains:
        if chainEn in matching_chains:
            chainDe = matching_chains[chainEn]

            num_en_mentions = len(en_coref_chains[chainEn])
            num_de_mentions = len(de_coref_chains[chainDe])

            if num_en_mentions == num_de_mentions:
                complete_matches[chainEn] = chainDe
                #temp.append(chainDe)
            else:
                partial_matches[chainEn] = chainDe
                #temp.append(chainDe)
        else:
            en_not_de[chainEn] = en_coref_chains[chainEn]

    for chainDE in de_coref_chains:
        if chainDE not in matched_germanchains:
            de_not_en[chainDE] = de_coref_chains[chainDE]


    #print("outgoing ====>")
    #print(len(complete_matches))
    #print(len(partial_matches))
    #print(len(en_not_de))
    #print(len(de_not_en))
    #print("total en out==>", len(complete_matches)+len(partial_matches)+len(en_not_de))
    #print("total de out==>", len(de_not_en)+len(set(temp)))# numbers match :)

    return complete_matches, partial_matches, en_not_de, de_not_en




#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------

def count_typology(dict_matches, en, de, enInfo, deInfo):
    """
    :param dict_matches: {'set_40': 'set_40', 'set_14': 'set_103',...}
    :param en:
    :param de:
    :return:
    """

    counts = {}
    for key in dict_matches:
        # order everything
        en_sort_men, en_sort_info = order_mention_types(en[key], enInfo[key])
        de_sort_men, de_sort_info = order_mention_types(de[dict_matches[key]], deInfo[dict_matches[key]])

        #equal legth case, for different lengths we don't know the correspondences
        for men in en_sort_info:
            pretty_men = "-".join(list(men))
            for mde in de_sort_info:
                pretty_mde = "-".join(list(mde))
                pair = pretty_men + " to " + pretty_mde
                if pair in counts:
                    counts[pair] += 1
                else:
                    counts[pair] = 1
    return counts



def count_uneven_length(dict_matches, en, de, enInfo, deInfo):

    en_longer_pairs = {}
    de_longer_pairs = {}
    equal = {}

    for key in dict_matches:
        # order everything
        en_sort_men, en_sort_info = order_mention_types(en[key], enInfo[key])
        de_sort_men, de_sort_info = order_mention_types(de[dict_matches[key]], deInfo[dict_matches[key]])
        # english longer than german
        if len(en_sort_men) > len(de_sort_men):
            en_longer_pairs[key] = dict_matches[key]
        elif len(en_sort_men) < len(de_sort_men):
            de_longer_pairs[key] = dict_matches[key]
        else:
            equal[key] = dict_matches[key] # should be empty

    return en_longer_pairs, de_longer_pairs, equal


def aggregate(d_doc, d_global):

    for key in d_doc:
        if key in d_global:
            d_global[key] += d_doc[key]
        else:
            d_global[key] = d_doc[key]




#############################################          MAIN            ##############################################
def main():
    if len(sys.argv) != 4:
        sys.stderr.write('Usage: {} {} {} {} \n'.format(sys.argv[0], "path_to_parcor-full", "subcorpus(news|DiscoMT|TED)", "alignment_file"))

        sys.exit(1)

    subcorpus = sys.argv[2]

    #DiscoMT files (hard coded to make sure they're in the very same order as the alignments file)
    endeDocs = ["000_1756_words.xml", "001_1819_words.xml", "002_1825_words.xml", "003_1894_words.xml",
                 "005_1938_words.xml", "006_1950_words.xml", "007_1953_words.xml", "009_2043_words.xml",
                 "010_205_words.xml", "011_2053_words.xml"]
    # news files
    # endeDocs = ["01_words.xml", "03_words.xml", "04_words.xml", "05_words.xml", "07_words.xml", "08_words.xml",
    #             "09_words.xml", "10_words.xml", "13_words.xml", "16_words.xml", "17_words.xml", "18_words.xml",
    #             "19_words.xml", "20_words.xml", "21_words.xml", "22_words.xml", "23_words.xml", "24_words.xml",
    #             "25_words.xml"]

    base_path = sys.argv[1]
    en_path_all = base_path + "/" + subcorpus + "/" + "EN"
    en_data_dir = en_path_all + "/" + "Basedata"
    en_annotation_dir = en_path_all + "/" + "Markables"

    de_path_all = base_path + "/" + subcorpus + "/" + "DE"
    de_data_dir = de_path_all + "/" + "Basedata"
    de_annotation_dir = de_path_all + "/" + "Markables"

    giza_alignments = read_alignments(sys.argv[3])
    mention_types_corpus = {}
    en_long_corpus, de_long_corpus = 0, 0
    equal_length_corpus, german_matched = 0, 0
    en_only_corpus = 0
    de_only_corpus = 0
    sanity_en, sanity_de, en_count, de_count = 0, 0, 0, 0

    for doc in endeDocs: #loop and keep order of protest
        #if doc[:4].isalpha():
        if subcorpus == "news":
            docid = re.findall(r'[0-9]+_?[0-9]+?', doc)[0]  # returns list therefore the index
        else:
            docid = re.findall(r'[0-9]+_[0-9]+', doc)[0]

        # document as single list of words
        en_document = create_document(en_data_dir, doc)
        de_document = create_document(de_data_dir, doc)

        en_sentences_ids = make_sentences_spans(docid, en_annotation_dir)
        de_sentences_ids = make_sentences_spans(docid, de_annotation_dir)

        #make alignments document level
        len_en = len(en_sentences_ids.keys())
        doc_aligns = make_doc_level_align(len_en, giza_alignments)
        reindexed_doc_aligns = transform_aligns(en_sentences_ids, de_sentences_ids, doc_aligns)

        #coref chains
        en_coref_chains, en_chains_info = get_chain_info(docid, en_annotation_dir)
        de_coref_chains, de_chains_info = get_chain_info(docid, de_annotation_dir)

        #filter chains
        en_filtered_chains = filter_chains(en_coref_chains, en_chains_info)
        de_filtered_chains = filter_chains(de_coref_chains, de_chains_info)
        # TODO: some documents (de news 07) are completely without chains after filtering

        #print some stats
        print_stats(en_path_all, doc, en_coref_chains, de_coref_chains, en_filtered_chains, de_filtered_chains)

        # chains' alignment points
        #align_of_en_chains = match_mentions_to_tgt(en_coref_chains, reindexed_doc_aligns)

        # find out chains correspondences between src & tgt

        scores = scoreChains(en_filtered_chains, de_filtered_chains, reindexed_doc_aligns)

        # printing out examples for the presentation
        for x in scores:
            for y in scores[x]:
                if scores[x][y] != 0:
                    print(x, y, scores[x][y])


        matching_chains = getHighest(scores)

        # print("matching dictionary!!!!!")
        # print(matching_chains)

        allMatch, someMatch, enNoMatch, deNoMatch = classifyMatches(en_filtered_chains, de_filtered_chains,
                                                                    matching_chains)

        # count mention correspondences in matches
        mention_types_doc = count_typology(allMatch, en_filtered_chains, de_filtered_chains, en_chains_info,
                                           de_chains_info)

        # count the uneven chains; same_long should be empty (sanity check)
        en_long, de_long, same_long = count_uneven_length(someMatch, en_filtered_chains, de_filtered_chains,
                                                           en_chains_info, de_chains_info)




        #count over corpus

        aggregate(mention_types_doc, mention_types_corpus)
        en_long_corpus += len(set(list(en_long.keys())))
        de_long_corpus += len(set(list(de_long.keys())))

        de_only_corpus += len(deNoMatch)
        en_only_corpus += len(enNoMatch)

        equal_length_corpus += len(set(list(allMatch.keys())))
        german_matched += len(set(list(allMatch.values())))

        #sanity check for the number of chains
        #print("sanity check")
        sanity_en += len(en_filtered_chains)
        sanity_de += len(de_filtered_chains)



        # ####print sanity check for indexes matching the words
        # print("sanity check")
        # print("##############################################")
        # for chain in en_filtered_chains:
        #     print(chain, en_filtered_chains[chain])
        #     actual_words = []
        #     for mention in en_filtered_chains[chain]:
        #         for word in mention:
        #             actual_words.append(en_document[word-1])
        #     print(actual_words)


        # printing out examples for presentation

        print("------------------------->")
        for chain in en_filtered_chains:
            if chain in ["set_119", "set_135", "set_225"]:
                print(chain, en_filtered_chains[chain])
                actual_words = []
                for mention in en_filtered_chains[chain]:
                    for word in mention:
                        actual_words.append(en_document[word-1])
                print(actual_words)



        for chain in de_filtered_chains:
            if chain in ["set_172", "set_171", "set_187", "set_188", "set_189", "set_36", "set_25"]:
                print(chain, de_filtered_chains[chain])
                actual_words = []
                for mention in de_filtered_chains[chain]:
                    for word in mention:
                        actual_words.append(de_document[word-1])
                print(actual_words)
        # # print out
        print("Matching chains ======>")
        print("\n")
        for englishkey in allMatch:
            germankey = allMatch[englishkey]
            print("English Chain:", englishkey, "German Chain:", germankey)
            en_tokens, en_types = prettify_chains(en_filtered_chains[englishkey], en_document, en_chains_info[englishkey])
            de_tokens, de_types = prettify_chains(de_filtered_chains[germankey], de_document, de_chains_info[germankey])
            print("Mentions tokens:")
            print(en_tokens)
            print(de_tokens)
            print("Mentions types")
            print(en_types)
            print(de_types)
            print("\n")

        print("Matching chains, different number of mentions ======>")
        print("\n")

        print("English longer chains ======>")
        print("\n")
        for englishkey in en_long:
            germankey = en_long[englishkey]
            print("English Chain:", englishkey, "German Chain:", germankey)
            en_tokens, en_types = prettify_chains(en_filtered_chains[englishkey], en_document, en_chains_info[englishkey])
            de_tokens, de_types = prettify_chains(de_filtered_chains[germankey], de_document, de_chains_info[germankey])
            print("Mentions tokens:")
            print(en_tokens)
            print(de_tokens)
            print("Mentions types")
            print(en_types)
            print(de_types)
            print("\n")

        print("German longer chains ======>")
        print("\n")
        for englishkey in de_long:
            germankey = de_long[englishkey]
            print("English Chain:", englishkey, "German Chain:", germankey)
            en_tokens, en_types = prettify_chains(en_filtered_chains[englishkey], en_document, en_chains_info[englishkey])
            de_tokens, de_types = prettify_chains(de_filtered_chains[germankey], de_document, de_chains_info[germankey])
            print("Mentions tokens:")
            print(en_tokens)
            print(de_tokens)
            print("Mentions types")
            print(en_types)
            print(de_types)
            print("\n")



        print("English chain not in German ======>")
        print("\n")
        for englishkey in enNoMatch:
            print("English Chain:", englishkey)
            en_tokens, en_types = prettify_chains(en_filtered_chains[englishkey], en_document, en_chains_info[englishkey])
            print("Mentions tokens:")
            print(en_tokens)
            print("Mentions types")
            print(en_types)
            print("\n")

        print("German chain not in English ======>")
        print("\n")
        for germankey in deNoMatch:
            print("German Chain:", germankey)
            de_tokens, de_types = prettify_chains(de_filtered_chains[germankey], de_document, de_chains_info[germankey])
            print("Mentions tokens:")
            print(de_tokens)
            print("Mentions types")
            print(de_types)
            print("\n")

        break


    print("\n")
    print("**************End of corpus*****************")

    print("**************Stats in corpus*****************")
    print("\n")
    print("mention correspondences in corpus (for matching chains with the same number of mentions)")
    print("\n")
    for w in sorted(mention_types_corpus, key=mention_types_corpus.get, reverse=True):
        print(w, mention_types_corpus[w])
    print("\n")
    print("number of matching chains:", equal_length_corpus)
    print("number of english chains longer than german:", en_long_corpus)
    print("number of german chains longer than german:", de_long_corpus)
    print("number of english chains not in german:", en_only_corpus)
    print("number of german chains not in english:", de_only_corpus)


    print("counts before classification: english", sanity_en, "german", sanity_de)



if __name__ == "__main__":
    main()



