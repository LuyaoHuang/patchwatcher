#!/usr/bin/env python

import os
import math
from utils import *
from nn import *
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='patchwatcher.log')


uselesslist = ['am','is','are','did','do', 'done','will','shall','would','should','to','on','for','at','in','we','i','my','mine','you','your','he','she','him','her','it',"it's",'however', 'which','where','of', 'the', 'a', 'an', 'about','above','under','after','by','with',"i'am","i'd","we're","they're"]

def splitpatchfromeml(emailfile):
    maildict = parsemail(emailfile)
    ret = splitpatchinternal(maildict)
    for n in ret.keys():
        print "patch name is %s" % n
        print "split it to group %d" % result[n][1]
        print ""

def splitpatchinternal(maildict):
    data = loaddata('./data.pkl')
    strlist = data[0]
    theta = data[1]
    xlist = []
    patchsethead = {}
    result = {}

    for n in maildict.keys():
        tmparray = []
        subpatch=[]
        tmplist = getinfo(maildict[n], subpatch=subpatch)
        if subpatch == []:
            for i in strlist:
                if i in tmplist:
                    tmparray.append(1.0)
                else:
                    tmparray.append(0.0)
        else:
            tmplist = []
            patchsethead[n] = subpatch
            for m in subpatch:
                if m not in maildict.keys():
                    logging.warning( "not find %s" % m)
                    continue
                tmplist.extend(getinfo(maildict[m]))
            for i in strlist:
                if i in tmplist:
                    tmparray.append(1.0)
                else:
                    tmparray.append(0.0)

        xlist.append(tmparray)

    x = numpy.array(xlist)
    x = x.T

    nn = NN(x.shape[0], int(math.sqrt(x.shape[0] + 3)), 3, lamda=0.001)
    y = nn.FPformin(x, theta).T
    logging.info( "try to split %d patches" % len(maildict))
    for n in range(len(y)):
        maxv = y[n].max()
        for i in range(len(y[n])):
            if y[n][i] != maxv:
                continue

            if manualfilter(maildict.values()[n]):
                result[maildict.keys()[n]] = [y[n], 4]
                break

            result[maildict.keys()[n]] = [y[n], i + 1]
            break

    for n in result.keys():
        if n in patchsethead.keys():
            group1=0
            group2=0
            group3=0
            group4=0
            for i in patchsethead[n]:
                if i not in result.keys():
                    continue

                if result[i][1] == 4:
                    group4 += 1
                if result[i][1] == 3:
                    group3 += 1
                if result[i][1] == 2:
                    group2 += 1
                if result[i][1] == 1:
                    group1 += 1

            if group4 > group3 and group4 > group2 and group4 > group3:
                result[n][1] = 4
                continue
            if group3 > group2 and group3 > group1 and group3 > group4:
                result[n][1] = 3
                continue
            if group2 > group3 and group2 > group1 and group2 > group4:
                result[n][1] = 2
                continue
            if group1 > group3 and group1 > group2 and group1 > group4:
                result[n][1] = 1
                continue

    return result, patchsethead
