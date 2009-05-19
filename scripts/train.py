#!/usr/bin/python

import common.dump
import hyperparameters, miscglobals

import common.options
hyperparameters.__dict__.update(common.options.reparse(hyperparameters.__dict__))
#miscglobals.__dict__ = common.options.reparse(miscglobals.__dict__)

from common import myyaml
import sys
print >> sys.stderr, myyaml.dump(common.dump.vars_seq([hyperparameters, miscglobals]))

rundir = common.dump.create_canonical_directory(hyperparameters.__dict__)

from common.stats import stats

import sys

import random, numpy
random.seed(miscglobals.RANDOMSEED)
numpy.random.seed(miscglobals.RANDOMSEED)

from common.file import myopen

from vocabulary import wordmap

import string

def read_vocabulary():
    for l in myopen(hyperparameters.VOCABULARY[hyperparameters.VOCABULARY_SIZE]):
        (cnt, word) = string.split(l)
        wordmap.id(word, can_add=True)
    wordmap.dump()
    wordmap.readonly = True

def get_train_example():
    for l in myopen(hyperparameters.TRAIN_SENTENCES):
        prevwords = []
        for w in string.split(l):
            w = string.strip(w)
            if wordmap.exists(w):
                prevwords.append(wordmap.id(w))
                if len(prevwords) >= hyperparameters.WINDOW_SIZE:
                    yield prevwords[-hyperparameters.WINDOW_SIZE:]
            else:
                prevwords = []

def get_validation_example():
    for l in myopen(hyperparameters.VALIDATION_SENTENCES):
        prevwords = []
        for w in string.split(l):
            w = string.strip(w)
            if wordmap.exists(w):
                prevwords.append(wordmap.id(w))
                if len(prevwords) >= hyperparameters.WINDOW_SIZE:
                    yield prevwords[-hyperparameters.WINDOW_SIZE:]
            else:
                prevwords = []

#ves = [e for e in get_validation_example()]
#import random
#random.shuffle(ves)
#for e in ves[:1000]:
#    print string.join([wordmap.str(id) for id in e])

print "Reading vocab"
read_vocabulary()

def validate(cnt):
    import math
    logranks = []
    print >> sys.stderr, "BEGINNING VALIDATION AT TRAINING STEP %d" % cnt
    print >> sys.stderr, stats()
    i = 0
    for (i, ve) in enumerate(get_validation_example()):
#        print >> sys.stderr, [wordmap.str(id) for id in ve]
        logranks.append(math.log(m.validate(ve)))
        if (i+1) % 10 == 0:
            print >> sys.stderr, "Training step %d, validating example %d, mean(logrank) = %.2f, stddev(logrank) = %.2f" % (cnt, i+1, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks)))
            print >> sys.stderr, stats()
    print >> sys.stderr, "FINAL VALIDATION AT TRAINING STEP %d: mean(logrank) = %.2f, stddev(logrank) = %.2f, cnt = %d" % (cnt, numpy.mean(numpy.array(logranks)), numpy.std(numpy.array(logranks)), i+1)
    print >> sys.stderr, stats()

def verbose_predict(cnt):
    for (i, ve) in enumerate(get_validation_example()):
        (score, prehidden) = m.verbose_predict(ve)
        abs_prehidden = numpy.abs(prehidden)
        med = numpy.median(abs_prehidden)
        abs_prehidden = abs_prehidden.tolist()
        assert len(abs_prehidden) == 1
        abs_prehidden = abs_prehidden[0]
        abs_prehidden.sort()
        abs_prehidden.reverse()
        print >> sys.stderr, cnt, "AbsPrehidden median =", med, "max =", abs_prehidden[:5]
        if i > 5: break

def visualize(cnt, WORDCNT=500):
    """
    Visualize a set of examples using t-SNE.
    """
    PERPLEXITY=30
    x = m.parameters.embeddings[:WORDCNT]
    print x.shape
    titles = [wordmap.str(id) for id in range(WORDCNT)]
    import os.path
    filename = os.path.join(rundir, "embeddings-%d.png" % cnt)
    try:
        from textSNE.calc_tsne import tsne
#       from textSNE.tsne import tsne
        out = tsne(x, perplexity=PERPLEXITY)
        from textSNE.render import render
        render([(title, point[0], point[1]) for title, point in zip(titles, out)], filename)
    except IOError:
        print >> sys.stderr, "ERROR visualizing", filename, ". Continuing..."



import model
m = model.Model()
#validate(0)
for (cnt, e) in enumerate(get_train_example()):
#    print [wordmap.str(id) for id in e]
    m.train(e)

    if (cnt+1) % 100 == 0:
        print >> sys.stderr, "Finished training step %d" % (cnt+1)
    if (cnt+1) % 10000 == 0:
        print >> sys.stderr, stats()
        verbose_predict(cnt+1)
    if (cnt+1) % hyperparameters.VALIDATE_EVERY == 0:
        validate(cnt+1)
        visualize(cnt+1)    
