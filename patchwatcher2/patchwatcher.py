#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchwatcher2.settings")

import django
django.setup()

import time
import lxml.etree as etree
import logging
import traceback
import hashlib
import socket

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='patchwatcher.log')

from splitpatch import splitpatchinternal
from utils import *
from patchwork.models import Dataset,currentwork,Patchinfos

LIBVIR_LIST = "https://www.redhat.com/archives/libvir-list"
LIBVIRT_REPO = "git://libvirt.org/libvirt.git"

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

def fixbreakpatchset(patchlink, newpatchset, fullcheck=False):
    ext = None
    new = None
    try:
        new = Dataset.objects.get(patchlink=patchlink)
        if not fullcheck:
            return new
    except Exception:
        logging.warning("cannot find %s in db, try to fix it" % patchlink)

    strings = getmaildata(patchlink)
    header = patchlink[:patchlink.find("msg")]
    info = parsehtmlpatch(strings, urlheader=header)

    if not new:
        try:
            ext = Dataset.objects.get(name=cleansubject(info[0])[1])
        except:
            pass

        m = hashlib.md5()
        m.update(patchlink)
        new = Dataset.objects.create(name=cleansubject(info[0])[1], desc=getdescfrommsg(info[3]),
                    group="others", patchlink=patchlink,
                    author=info[1],date=transtime(info[2]),
                    testcase='N/A',testby='N/A',state='ToDo',buglink="N/A", md5lable=m.hexdigest())
        logging.info("create a new obj in db which link is %s" % patchlink)
        newpatchset.append(patchlink)

    if ext:
        new.group = ext.group
        new.save()

    for i in info[4]["Follow-Ups"].keys():
        sitems = fixbreakpatchset(info[4]["Follow-Ups"][i], newpatchset)
        if not sitems:
            continue

        new.subpatch.add(sitems)

    for i in info[4]["References"].keys():
        sitems = fixbreakpatchset(info[4]["References"][i], newpatchset)
        if not sitems:
            continue

        new.subpatch.add(sitems)

    return new

def sendpatchinfo(newpatchset, configure):
    skiplist = []
    for i in newpatchset:
        obj = Dataset.objects.get(patchlink=i)
        if len(obj.subpatch.all()) > 1:
            for n in obj.subpatch.all():
                skiplist.append(n.patchlink)
        elif len(obj.subpatch.all()) == 1 and obj.subpatch.all()[0].patchlink != obj.patchlink:
            """ so not sure for right now """
            skiplist.append(i)

    for i in newpatchset:
        if i in skiplist:
            continue

        if not configure["serverip"]:
            hostip = socket.gethostbyname(socket.gethostname())
        else:
            hostip = configure["serverip"]

        tmpdict = {"patchurl" : "http://%s:8888/patchfile/%s" % (hostip, Dataset.objects.get(patchlink=i).md5lable)}
        try:
            jenkinsJobTrigger({"_patchurl_": tmpdict["patchurl"]}, configure)
        except:
            logging.error("Fail to trigger a jenkins job")
            return

        try:
            pikasendmsg(configure['server'], str(tmpdict), "patchwatcher")
        except pika.exceptions.AMQPConnectionError:
            logging.warning("cannot connect to "+configure['server'])
            return

def updatepatchinfo(groupinfo, patchset, patchinfo, newpatchset):
    tmppatchset = {}
    for n in groupinfo.keys():
        if n not in patchinfo.keys():
            raise ValueError, 'cannot find % link' % n

        if int(groupinfo[n][1]) < 4:
            group = 'group%s' % groupinfo[n][1]
        else:
            group = 'others'

        buglink = "N/A"
        if "buglist" in patchinfo[n].keys():
            if len(patchinfo[n]["buglist"]) > 1:
                buglink = genbuglist(patchinfo[n]["buglist"])
            elif len(patchinfo[n]["buglist"]) == 1:
                buglink = patchinfo[n]["buglist"][0]

        if patchinfo[n]["patchset"]["Follow-Ups"] != {} \
                or patchinfo[n]["patchset"]["References"] != {}:
            tmppatchset[patchinfo[n]["patchlink"]] = [n, patchinfo[n]["patchset"]]

        try:
            """Update buglink to exist item"""
            tmpdate = Dataset.objects.get(patchlink=patchinfo[n]["patchlink"])
            tmpdate.buglink = buglink
            tmpdate.save()
            continue
        except Exception:
            pass

        m = hashlib.md5()
        m.update(patchinfo[n]["patchlink"])
        Dataset.objects.create(name=n, desc=patchinfo[n]["desc"],
                    group=group, patchlink=patchinfo[n]["patchlink"],
                    author=patchinfo[n]["author"],date=transtime(patchinfo[n]["date"]),
                    testcase='N/A',testby='N/A',state='ToDo',buglink=buglink, md5lable=m.hexdigest())
        newpatchset.append(patchinfo[n]["patchlink"])

    for n in tmppatchset.keys():
        checkpatchset = True
        name = tmppatchset[n][0]
        subpatch = tmppatchset[n][1]
        if name not in patchset.keys():
            logging.warning("cannot find %s in patchset" % name)
            checkpatchset = False

        try:
            item = Dataset.objects.get(patchlink=n)
        except Exception:
            logging.warning("cannot find %s in db" % n)
            continue

        for i in subpatch["Follow-Ups"].keys():
            if checkpatchset == True and i not in patchset[name]:
                logging.warning("cannot find %s in patchset for %s" % (i, name))

            sitems = fixbreakpatchset(subpatch["Follow-Ups"][i], newpatchset)
            if not sitems:
                continue

            item.subpatch.add(sitems)

        for i in subpatch["References"].keys():
            if checkpatchset == True and i not in patchset[name]:
                logging.warning("cannot find %s in patchset for %s" % (i, name))

            sitems = fixbreakpatchset(subpatch["References"][i], newpatchset)
            if not sitems:
                continue

            item.subpatch.add(sitems)

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
                    if "Re:" in patchname or "PATCH" not in patchname:
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

def getmailwithdate(maillist, start, end=None, skipbz=True):
    if not end:
        """ get current date """
        end = time.strftime("%Y-%m")

    maildict = parsedatemail(maillist, start[0], end, start[1])
    maildict2 = {}
    buglist = {}
    patchinfo = {}
    lastmsginfo = start
    for year in maildict.keys():
        for month in maildict[year].keys():
            for msgid in maildict[year][month]:
                hreflist = []
                link = genurlofpatch(maillist, year, month, msgid)
                strings = getmaildata(link)
                try:
                    info = parsehtmlpatch(strings, hreflist, genurlofpatchhead(maillist, year, month))
                except StructError:
                    logging.error("Cannot parse "+link)
                    continue

                if skipbz:
                    """ record the patch which already have bz """
                    if "bugzilla.redhat.com" in info[3]:
                        logging.info("find a patch named %s it has bugzilla" % cleansubject(info[0])[1])
                        buglist[cleansubject(info[0])[1]] = hreflist

                maildict2[cleansubject(info[0])[1]] = info[3]
                patchinfo[cleansubject(info[0])[1]] = { "patchlink" :link,
                                                        "desc" :getdescfrommsg(info[3]),
                                                        "author":info[1],
                                                        "date":info[2],
                                                        "patchset":info[4]}
                lastmsginfo = ['%s-%s' % (year, month), str(msgid)]

    if lastmsginfo == start:
        return

    result, patchset = splitpatchinternal(maildict2)

    for n in buglist.keys():
        for i in patchset.keys():
            if n in patchset[i]:
                if "buglist" in patchinfo[i].keys():
                    patchinfo[i]["buglist"].extend(buglist[n])
                else:
                    patchinfo[i]["buglist"] = buglist[n]

        patchinfo[n]["buglist"] = buglist[n]

    return result, patchset, patchinfo, lastmsginfo

def watchlibvirtrepo(checkall=False):
    if not os.access("./libvirt", os.O_RDONLY):
        logging.info("Cannot find libvirt source code")
        logging.info("Download libvirt source code")
        downloadsourcecode(LIBVIRT_REPO)
        return watchlibvirtrepo()

    callgitpull("./libvirt")
    if len(Patchinfos.objects.all()) == 0:
        startdate = Dataset.objects.order_by("date")[0].date.replace(tzinfo=None)
        enddate = currenttime()
        logmsg = getgitlog("./libvirt", startdate, enddate)
        if not logmsg:
            return

        for n in logmsg.splitlines():
            tmplist = Dataset.objects.filter(name = n[n.find(" ")+1:])
            for tmp in tmplist:
                tmp.pushed = "Yes"
                tmp.save()
                logging.debug("update %s pushed status to yes" % tmp.name)

        Patchinfos.objects.create(startdate=startdate, enddate=enddate)

    else:
        Patchinfo = Patchinfos.objects.all()[0]
        startdate = Dataset.objects.order_by("date")[0].date.replace(tzinfo=None)
        enddate = currenttime()
        if checkall:
            logmsg = getgitlog("./libvirt", startdate, enddate)
            if not logmsg:
                return

            for n in logmsg.splitlines():
                tmplist = Dataset.objects.filter(name = n[n.find(" ")+1:])
                for tmp in tmplist:
                    tmp.pushed = "Yes"
                    tmp.save()
                    logging.debug("update %s pushed status to yes" % tmp.name)

            Patchinfo.startdate = startdate
            Patchinfo.enddate = enddate
            Patchinfo.save()

        if startdate < Patchinfo.startdate.replace(tzinfo=None):
            logmsg = getgitlog("./libvirt", startdate, Patchinfo.startdate)
            if not logmsg:
                return

            for n in logmsg.splitlines():
                tmplist = Dataset.objects.filter(name = n[n.find(" ")+1:])
                for tmp in tmplist:
                    tmp.pushed = "Yes"
                    tmp.save()
                    logging.debug("update %s pushed status to yes" % tmp.name)

            Patchinfo.startdate = startdate
            Patchinfo.save()
        if enddate > Patchinfo.enddate.replace(tzinfo=None):
            logmsg = getgitlog("./libvirt", Patchinfo.enddate, enddate)
            if not logmsg:
                return

            for n in logmsg.splitlines():
                tmplist = Dataset.objects.filter(name = n[n.find(" ")+1:])
                for tmp in tmplist:
                    tmp.pushed = "Yes"
                    tmp.save()
                    logging.debug("update %s pushed status to yes" % tmp.name)

            Patchinfo.enddate = enddate
            Patchinfo.save()

def patchwatcher():
    start = ['2016-6', '01005']
    count = 0
    firstinit=True
    config = loadconfig()
    for i in ["mqserver", "serverip", "jenkins_job_url", "jenkins_job_token", "jenkins_job_parameter", "verify"]:
        if i not in config.keys():
            raise Exception("no %s in config file" % i)

    while 1:
        newpatchset = []

        count += 1
        if count%6 == 0:
            logging.info("backups db")
            bakdb()

        if loaddateinfo():
            start = loaddateinfo()

        try:
            groupinfo, patchset, patchinfo, lastmsginfo = getmailwithdate(LIBVIR_LIST, start)
        except Exception, e:
            logging.info("Exception: %s" % e)
            print traceback.format_exc()
            watchlibvirtrepo(firstinit)
            time.sleep(600)
            firstinit=False
            continue

        logging.info("update %d patches" % len(groupinfo))
        updatepatchinfo(groupinfo, patchset, patchinfo, newpatchset)
        freshdateinfo(lastmsginfo)
        sendpatchinfo(newpatchset, config)
        watchlibvirtrepo(firstinit)
        time.sleep(600)
        firstinit=False

if __name__ == '__main__':
    patchwatcher()
