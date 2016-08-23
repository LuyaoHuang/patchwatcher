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

def split_patch_from_eml(emailfile):
    maildict = parsemail(emailfile)
    ret = split_patch_internal(maildict)
    for n in ret.keys():
        print "patch name is %s" % n
        print "split it to group %d" % result[n][1]
        print ""

def split_patch_internal(maildict, data_base=None):
    if not data_base:
        data = loaddata('data.pkl')
    else:
        data = loaddata(data_base)

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
            group_info = [0, 0, 0, 0]
            for i in patchsethead[n]:
                if i not in result.keys():
                    continue

                group_info[result[i][1] - 1] += 1

            result[n][1] = group_info.index(max(group_info)) + 1

    return result, patchsethead
