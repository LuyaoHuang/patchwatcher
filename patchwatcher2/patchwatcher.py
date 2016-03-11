#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchwatcher2.settings")

import django
django.setup()

import time
import lxml.etree as etree
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='patchwatcher.log',
                    filemode='w')

from splitpatch import splitpatchinternal
from utils import *
from patchwork.models import *

LIBVIR_LIST = "https://www.redhat.com/archives/libvir-list"

def freshdateinfo(date):
    try:
        currentwork.delete(currentwork.objects.all()[0])
    except IndexError:
        pass

    currentwork.objects.create(date=date[0], msgid = date[1])

def loaddateinfo():
    try:
        date = currentwork.objects.all()[0]
    except IndexError:
        return
    return [date.date, date.msgid]

def updatepatchinfo(groupinfo, patchset, patchlink):
    skippatch = []
    for n in patchset.values():
        skippatch.extend(n)

    for n in groupinfo.keys():
        if n in skippatch:
            continue
        if n not in patchlink.keys():
            raise ValueError, 'cannot find % link' % n

        if int(groupinfo[n][1]) < 4:
            group = 'group%s' % groupinfo[n][1]
        else:
            group = 'others'

        buglink = "N/A"
        if len(patchlink[n]) == 5:
            if len(patchlink[n][4]) > 1:
                buglink = genbuglist(patchlink[n][4])
            elif len(patchlink[n][4]) == 1:
                buglink = patchlink[n][4][0]

        Dataset.objects.create(name=n, desc=patchlink[n][1],
                                group=group, patchlink=patchlink[n][0],
                                author=patchlink[n][2],date=transtime(patchlink[n][3]),
                                testcase='N/A',testby='N/A',state='ToDo',buglink=buglink)

def parsedatemail(maillist, startdate, enddate, startmsgid):
    retdict = {}
    startdatelist = startdate.split('-')
    enddatelist = enddate.split('-')
    startmonth = startdatelist[1]
    startyear = int(startdatelist[0])
    firstmonth = True
    while int(startyear) <= int(enddatelist[0]):
        if int(startyear) != int(enddatelist[0]):
            endmonth = 12
        else:
            endmonth = enddatelist[1]

        retdict[startyear] = {}
        while int(startmonth) <= int(endmonth):
            mailids = []

            link = genurloflist(maillist, '%s-%s' % (startdatelist[0], startmonth))
            strings = getmaildata(link)
            xml = etree.HTML(strings)
            ul = xml.xpath('/html/body/ul')
            for n in ul[1:]:
                for li in n.getchildren():
                    tmpmsgid = li.getchildren()[0].get('name')
                    patchname = li.getchildren()[0].text
                    if patchname[:3] == 'Re:' or patchname.find('PATCH') < 0:
                        continue

                    if firstmonth:
                        if int(tmpmsgid) <= int(startmsgid):
                            continue

                    mailids.append(tmpmsgid)

            retdict[startyear][int(startmonth)] = mailids

            startmonth = int(startmonth) + 1
            if firstmonth:
                firstmonth = False

        startyear = int(startyear) + 1
        startmonth = 1

    return retdict

def getmailwithdate(maillist, start, end, skipbz=True):
    if end == []:
        """ get current date """
        end.append(time.strftime("%Y-%m"))

    maildict = parsedatemail(maillist, start[0], end[0], start[1])
    maildict2 = {}
    buglist = {}
    patchlink = {}
    lastmsginfo = start
    for year in maildict.keys():
        for month in maildict[year].keys():
            for msgid in maildict[year][month]:
                hreflist = []
                link = genurlofpatch(maillist, year, month, msgid)
                strings = getmaildata(link)
                info = parsehtmlpatch(strings, hreflist)
                if skipbz:
                    """ skip the patch which already have bz """
                    if "bugzilla.redhat.com" in info[3]:
                        logging.info("skip a patch named %s it has bugzilla" % cleansubject(info[0])[1])
                        buglist[cleansubject(info[0])[1]] = hreflist

                maildict2[cleansubject(info[0])[1]] = info[3]
                patchlink[cleansubject(info[0])[1]] = [link, getdescfrommsg(info[3]), info[1], info[2]]
                lastmsginfo = ['%s-%s' % (year, month), str(msgid)]

    if lastmsginfo == start:
        return

    result, patchset = splitpatchinternal(maildict2)

    for n in buglist.keys():
        for i in patchset.keys():
            if n in patchset[i]:
                if len(patchlink[i]) == 5:
                    patchlink[i][4].extend(buglist[n])
                else:
                    patchlink[i].append(buglist[n])

        patchlink[n].append(buglist[n])

    return result, patchset, patchlink, lastmsginfo

def patchwatcher():
    start = ['2016-3', '00000']
    end = []
    count = 0

    while 1:
        count += 1
        if count%6 == 0:
            logging.info("backups db")
            bakdb()

        if loaddateinfo():
            start = loaddateinfo()

        try:
            groupinfo, patchset, patchlink, lastmsginfo = getmailwithdate(LIBVIR_LIST, start, end)
        except TypeError, KeyError:
            time.sleep(600)
            continue

        logging.info("update %d patches" % len(groupinfo))
        updatepatchinfo(groupinfo, patchset, patchlink)
        freshdateinfo(lastmsginfo)
        time.sleep(600)

if __name__ == '__main__':
    patchwatcher()
