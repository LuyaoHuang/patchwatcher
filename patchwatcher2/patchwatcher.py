#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchwatcher2.settings")

import django
django.setup()

import time
import lxml.etree as etree
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

        group = 'group%s' % groupinfo[n][1]
        Dataset.objects.create(name=n, desc=patchlink[n][1],
                                group=group, patchlink=patchlink[n][0],
                                author=patchlink[n][2],date=patchlink[n][3],
                                testcase='N/A',testby='N/A',state='ToDo')

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

def getmailwithdate(maillist, start, end):
    if end == []:
        """ get current date """
        end.append(time.strftime("%Y-%m"))

    maildict = parsedatemail(maillist, start[0], end[0], start[1])
    maildict2 = {}
    patchlink = {}
    lastmsginfo = start
    for year in maildict.keys():
        for month in maildict[year].keys():
            for msgid in maildict[year][month]:
                link = genurlofpatch(maillist, year, month, msgid)
                strings = getmaildata(link)
                info = parsehtmlpatch(strings)
                maildict2[cleansubject(info[0])[1]] = info[3]
                patchlink[cleansubject(info[0])[1]] = [link, getdescfrommsg(info[3]), info[1], info[2]]
                lastmsginfo = ['%s-%s' % (year, month), str(msgid)]

    if lastmsginfo == start:
        return

    freshdateinfo(lastmsginfo)
    result, patchset = splitpatchinternal(maildict2)

    return result, patchset, patchlink

def patchwatcher():
    start = ['2016-3', '00044']
    end = []

    while 1:
        if loaddateinfo():
            start = loaddateinfo()

        try:
            groupinfo, patchset, patchlink = getmailwithdate(LIBVIR_LIST, start, end)
        except TypeError:
            time.sleep(10)
            continue

        print "update %d patches" % len(groupinfo)
        updatepatchinfo(groupinfo, patchset, patchlink)
        time.sleep(10)

if __name__ == '__main__':
    patchwatcher()
