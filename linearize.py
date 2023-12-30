#!/usr/bin/env python3

from xml.etree import ElementTree as ET
import re
from collections import defaultdict

DEP_RE = re.compile(r'<#(\d+)→(\d+)>')

class LU:
    def __init__(self, wblank, form):
        self.wblank = wblank
        self.form = form
        self.lemma, self.tags = form.split('<', 1)
        self.tags = '<' + self.tags
        self.idx = 0
        self.parent = 0
        self.dep_span = None
        m = DEP_RE.search(self.form)
        if m is not None:
            self.idx = int(m.group(1))
            self.parent = int(m.group(2))
            self.dep_span = m.span()
        self.rel = None
        if '@' in self.tags:
            i = self.tags.index('@')
            self.rel = self.tags[i+1].split('>')[0]
    def write(self, idx, parent):
        ret = self.wblank
        if self.idx is None:
            ret += '^' + self.form + '$'
        else:
            ret += '^' + self.form[:self.dep_span[0]]
            ret += '<#' + str(idx) + '→' + str(parent) + '>'
            ret += self.form[self.dep_span[1]:] + '$'
        return ret

class NodePattern:
    def __init__(self):
        self.lemma = None
        self.tags = None
        self.rel = None
        self.parent = False
    def from_xml(node):
        ret = NodePattern()
        ret.lemma = node.attrib.get('lemma')
        tg = node.attrib.get('tags')
        if tg is not None:
            tls = tg.split('.')
            pat = ''
            for t in tls:
                if t == '*':
                    pat += '(<[^<>]+>)*'
                elif t == '+':
                    pat += '(<[^<>]+>)+'
                elif t == '?':
                    pat += '(<[^<>]+>)'
                else:
                    pat += '<' + t + '>'
            pat += '(<@|<#|$)'
            ret.tags = re.compile(pat)
        ret.rel = node.attrib.get('rel')
        ret.parent = (node.attrib.get('parent', 'no').lower() == 'yes')
        return ret
    def match(self, lu):
        if self.lemma is not None and self.lemma != lu.lemma:
            return False
        if self.rel is not None and self.rel != lu.rel:
            return False
        if self.tags is not None and self.tags.search(lu.tags) is None:
            return False
        return True

class OrderRule:
    def __init__(self, node1, node2, weight, direction):
        self.node1 = node1
        self.node2 = node2
        self.weight = weight
        self.direction = direction
    def from_xml(node):
        if len(node) != 2:
            raise ValueError('<pair> node should have exactly 2 children')
        n1 = NodePattern.from_xml(node[0])
        n2 = NodePattern.from_xml(node[1])
        w = float(node.attrib.get('weight', '1.0'))
        o = node.attrib.get('order', 'LR')
        return OrderRule(n1, n2, w, o)

def load_xml(fname):
    doc = ET.parse(fname)
    ret = []
    for p in doc.getroot().findall('pair'):
        ret.append(OrderRule.from_xml(p))
    # TODO: reorder rules
    return ret

def apply_rules(sentence, rules):
    dct = defaultdict(lambda: 0)
    for r in rules:
        for i, w1 in enumerate(sentence):
            if not r.node1.match(w1):
                continue
            for j, w2 in enumerate(sentence):
                if i == j:
                    continue
                if r.node1.parent:
                    if w1.idx != w2.parent:
                        continue
                elif r.node2.parent:
                    if w1.parent != w2.idx:
                        continue
                else:
                    if w1.parent != w2.parent:
                        continue
                if not r.node2.match(w2):
                    continue
                if r.direction == 'LR':
                    dct[(w1.idx, w2.idx)] += r.weight
                else:
                    dct[(w1.idx, w2.idx)] -= r.weight
    return dct
                    
# TODO:
# - parse LUs from stdin, splitting into sentences
# - reordering rules
# - sorting words
# - output
