import argparse
import bisect
import collections
import difflib
import pathlib
import sys

from lxml import etree


def wa_to_dict(word_alignment):
    wa = collections.defaultdict(list)
    for s, t in word_alignment:
        wa[s].append(t)
    return wa


class WordAlignment:
    def __init__(self, wa_file, src_sentences, tgt_sentences):
        self.alignment = []
        for line, (ss, se), (ts, te) in zip(wa_file, src_sentences, tgt_sentences):
            for ap in line.rstrip('\n').split(' '):
                si, ti = (int(x) for x in ap.split('-'))
                self.alignment.append((ss + si, ts + ti))
        self.s2t = wa_to_dict(self.alignment)
        self.t2s = wa_to_dict((t, s) for s, t in self.alignment)


class MMAXFile:
    def __init__(self, mmax_file, sentence_level='sentence'):
        self.levels = {}

        mmax_file_path = pathlib.Path(mmax_file)
        self.path = mmax_file_path.parent
        self.markable_path = self.path / 'Markables'
        self.mmax_id = mmax_file_path.stem

        with open(self.path / 'Basedata' / (self.mmax_id + '_words.xml'), 'r') as f:
            words_xml = etree.parse(f)

        self.words = [mrk.text for mrk in words_xml.iter('word')]

        sntlvl = self.load_level(sentence_level)
        sntlvl.markables.sort(key=lambda mrk: int(mrk.get('orderid')))
        self.sentences = [span_to_range(mrk.get('span')) for mrk in sntlvl.markables]

    def load_level(self, level):
        if level not in self.levels:
            markable_tag = '{www.eml.org/NameSpaces/%s}markable' % level
            xml_file = self.markable_path / ('%s_%s_level.xml' % (self.mmax_id, level))
            with open(xml_file, 'r') as f:
                xml = etree.parse(f)
            self.levels[level] = MMAXLevel(xml.iter(markable_tag), len(self.words))
        return self.levels[level]

    def markable_to_string(self, mrk):
        special = mrk.get('SPECIAL')
        if special:
            return special

        span = mrk.get('span')
        parts = []
        for part in span.split(','):
            s, e = span_to_range(part)
            parts.append(' '.join(self.words[s:e]))
        return '[' + '|'.join(parts) + ']'


def span_to_positions(span):
    pos = []
    for part in span.split(','):
        pos.extend(range(*span_to_range(part)))
    return pos


def span_to_range(span):
    if ',' in span:
        raise ValueError('Span must be contiguous: ' + span)
    ep = span.split('..')
    start = int(ep[0].lstrip('word_')) - 1
    end = int(ep[1].lstrip('word_')) if len(ep) == 2 else start + 1
    return start, end


class MMAXLevel:
    def __init__(self, mrk_iter, corpus_size):
        self.markables = list(mrk_iter)
        self.markables_at_pos = [[] for _ in range(corpus_size)]
        for mrk in self.markables:
            for i in span_to_positions(mrk.get('span')):
                self.markables_at_pos[i].append(mrk)


def get_coref_chains(mmax):
    coref_level = mmax.load_level('coref')
    chains = collections.defaultdict(list)
    for mrk in coref_level.markables:
        coref_class = mrk.get('coref_class')
        if coref_class and coref_class != 'empty':
            chains[coref_class].append(mrk)
    for ch in chains.values():
        ch.sort(key=lambda m: min(span_to_positions(m.get('span'))))
    return dict(chains)


def get_chain_pos(chain):
    return set().union(*(span_to_positions(mrk.get('span')) for mrk in chain))


def align_chains(src_chains, tgt_chains, word_alignment):
    src_pos = {k: get_chain_pos(ch) for k, ch in src_chains.items()}
    tgt_pos = {k: get_chain_pos(ch) for k, ch in tgt_chains.items()}
    proj_s2t = {k: set().union(*(word_alignment.s2t[x] for x in ch)) for k, ch in src_pos.items()}
    proj_t2s = {k: set().union(*(word_alignment.t2s[x] for x in ch)) for k, ch in tgt_pos.items()}

    scores = collections.defaultdict(lambda: collections.defaultdict(lambda: 0.0))

    for i, sp in src_pos.items():
        for j, tp in proj_t2s.items():
            s = len(sp.intersection(tp)) / 2
            if s > 0:
                scores[i][j] = s

    for i, tp in tgt_pos.items():
        for j, sp in proj_s2t.items():
            s = len(sp.intersection(tp)) / 2
            if s > 0:
                scores[j][i] += s

    triples = [(i, j, s) for i, x in scores.items() for j, s in x.items()]
    chains_s2t = {}
    chains_t2s = {}

    for i, j, s in sorted(triples, key=lambda t: t[2], reverse=True):
        if i not in chains_s2t and j not in chains_t2s:
            chains_s2t[i] = j
            chains_t2s[j] = i

    return chains_s2t, chains_t2s


def align_mentions(src_chains, tgt_chains, chains_s2t, word_alignment):
    aligned = []
    for sc, tc in chains_s2t.items():
        src = src_chains[sc]
        tgt = tgt_chains[tc]
        src_pos = [set(span_to_positions(mrk.get('span'))) for mrk in src]
        tgt_pos = [set(span_to_positions(mrk.get('span'))) for mrk in tgt]
        proj_s2t = [set().union(*(word_alignment.s2t[x] for x in pos)) for pos in src_pos]
        proj_t2s = [set().union(*(word_alignment.t2s[x] for x in pos)) for pos in tgt_pos]

        scores = collections.defaultdict(lambda: collections.defaultdict(lambda: 0.0))

        for i, sp in enumerate(src_pos):
            for j, tp in enumerate(proj_t2s):
                s = len(sp.intersection(tp)) / 2
                if s > 0:
                    scores[i][j] = s

        for i, tp in enumerate(tgt_pos):
            for j, sp in enumerate(proj_s2t):
                s = len(sp.intersection(tp)) / 2
                if s > 0:
                    scores[j][i] = s

        triples = [(i, j, s) for i, x in scores.items() for j, s in x.items()]
        covered_src = set()
        covered_tgt = set()

        for i, j, s in sorted(triples, key=lambda t: t[2], reverse=True):
            if i not in covered_src and j not in covered_tgt:
                aligned.append((src[i], tgt[j]))
                covered_src.add(i)
                covered_tgt.add(j)

    return aligned


def format_passage(mmax, markables, fromsnt, tosnt):
    highlight = {}
    for tag, mrk in markables:
        pos = span_to_positions(mrk.get('span'))
        for p in pos:
            highlight[p] = tag

    out = ''
    for start, end in mmax.sentences[fromsnt:tosnt]:
        for p in range(start, end):
            if p in highlight:
                out += '<span class="%s">%s</span>\n' % (highlight[p], mmax.words[p])
            else:
                out += mmax.words[p] + '\n'
        out += '<br/>\n'

    return out


def sentence_span(mmax, markables):
    min_pos = sys.maxsize
    max_pos = 0
    for mrk in markables:
        pos = span_to_positions(mrk.get('span'))
        min_pos = min(min_pos, *pos)
        max_pos = max(max_pos, *pos)

    sntstart = [start for start, end in mmax.sentences]
    fromsnt = bisect.bisect(sntstart, min_pos) - 1
    tosnt = bisect.bisect(sntstart, max_pos)

    return fromsnt, tosnt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-src', required=True, help='Source language MMAX file')
    parser.add_argument('-src_sentence', default='sentence', help='SL sentence level name')
    parser.add_argument('-tgt', required=True, help='Target language MMAX file')
    parser.add_argument('-tgt_sentence', default='sentence', help='TL sentence level name')
    parser.add_argument('-alig', required=True, help='Word alignments')
    args = parser.parse_args()

    src = MMAXFile(args.src)
    tgt = MMAXFile(args.tgt)

    with open(args.alig, 'r') as f:
        word_alignment = WordAlignment(f, src.sentences, tgt.sentences)

    src_chains = get_coref_chains(src)
    tgt_chains = get_coref_chains(tgt)

    chains_s2t, chains_t2s = align_chains(src_chains, tgt_chains, word_alignment)
    mentions_s2t = align_mentions(src_chains, tgt_chains, chains_s2t, word_alignment)
    mid_t2s = {t.get('id'): s.get('id') for s, t in mentions_s2t}

    mismatches = []

    for s_chain_id, t_chain_id in chains_s2t.items():
        s_chain = src_chains[s_chain_id]
        t_chain = tgt_chains[t_chain_id]
        s_id = [x.get('id') for x in s_chain]
        t_id = [x.get('id') for x in t_chain]
        t_proj_id = [mid_t2s[x] if x in mid_t2s else 'TGT:' + x for x in t_id]
        matcher = difflib.SequenceMatcher(a=s_id, b=t_proj_id, autojunk=False)
        mismatches.extend((s_chain_id, t_chain_id) + x for x in matcher.get_opcodes() if x[0] != 'equal')

    out = '''<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8"/>
    <title>Chain differences</title></head>
    <style>
    .context { color: #1b9e77; text-decoration-line: underline; }
    .insert { color: #d95f02; text-decoration-line: underline; }
    .replace { color: #cc33ff; text-decoration-line: underline; }
    .delete { color: #e7298a; text-decoration-line: underline; }
    </style>
    <body>
    <span class="context">context</span>
    <span class="insert">insert</span>
    <span class="replace">replace</span>
    <span class="delete">delete</span>
    <hr/>
    '''
    for s_chain_id, t_chain_id, tag, i1, i2, j1, j2 in mismatches:
        s_chain = src_chains[s_chain_id]
        t_chain = tgt_chains[t_chain_id]
        s_markables = []
        t_markables = []
        if i1 > 0:
            s_markables.append(('context', s_chain[i1 - 1]))
        if j1 > 0:
            t_markables.append(('context', t_chain[j1 - 1]))
        s_markables.extend((tag, mrk) for mrk in s_chain[i1:i2])
        t_markables.extend((tag, mrk) for mrk in t_chain[j1:j2])
        if i2 < len(s_chain) - 1:
            s_markables.append(('context', s_chain[i2 + 1]))
        if j2 < len(t_chain) - 1:
            t_markables.append(('context', t_chain[j2 + 1]))

        s_fromsnt, s_tosnt = sentence_span(src, (mrk for _, mrk in s_markables))
        t_fromsnt, t_tosnt = sentence_span(tgt, (mrk for _, mrk in t_markables))
        fromsnt = min(s_fromsnt, t_fromsnt)
        tosnt = max(s_tosnt, t_tosnt)

        out += '<p>\n'
        out += format_passage(src, s_markables, fromsnt, tosnt)
        out += '</p>\n'
        out += '<p>\n'
        out += format_passage(tgt, t_markables, fromsnt, tosnt)
        out += '</p>\n'
        out += '<hr/>\n'
    out += '</html>'

    with open('output.html', 'w') as f:
        print(out, file=f)


if __name__ == '__main__':
    main()
