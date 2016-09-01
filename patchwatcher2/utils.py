#!/usr/bin/env python

import glob
import lxml.etree as etree
import random
import subprocess
from subprocess import STDOUT
import re
import cPickle as pickle
import os
from dateutil import parser
import time
import yaml
import logging
import urllib2
import pika
import requests

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='patchwatcher.log')
logging.getLogger("pika").propagate = False

group1 = ['src/storage/','src/qemu/qemu_blockjob.c']
group2 = ['src/network/','src/cpu/','src/interface/', 'src/node_device/','src/nwfilter/','src/util/virnuma.c',]
group3 = ['src/security/','src/qemu/qemu_agent.c','src/qemu/qemu_migration.c','src/logging/']

notsupport = ['src/libxl','src/bhyve','src/xen','src/esx','src/hyperv','src/parallels','src/openvz','src/phyp','src/uml','src/vbox','src/vmware','src/vmx','src/vz','src/xenapi','src/xenconfig']

MONTH = {'12':'December',
         '11':'November',
         '10':'October',
         '9':'September',
         '8':'August',
         '7':'July',
         '6':'June',
         '5':'May',
         '4':'April',
         '3':'March',
         '2':'February',
         '1':'January',
         }

class StructError(Exception):
    def __init__(self, info):
        self.info = info

    def __str__(self):
        return repr(self.info)

def genbuglist(buglist):
    ret = 'https://bugzilla.redhat.com/buglist.cgi?bug_id='
    tmplist = []
    for n in buglist:
        if not re.match('^https://bugzilla.redhat.com/', n):
            continue

        if n.split('=')[-1] not in tmplist:
            tmplist.append(n.split('=')[-1])

    if not tmplist:
        logging.info("Find a strange bug list %s" % str(buglist))
        return

    for n in tmplist[:-1]:
        ret += '%s,' % n
    ret += tmplist[-1]
    return ret

def transtime(time):
    return parser.parse(time)

def currenttime():
    return parser.parse(time.ctime()).replace(tzinfo=None)

def bakdb():
    if not os.path.exists('./dbbak/'):
        return
    cmd = "cp -f db.sqlite3 ./dbbak/"
    output = subprocess.check_output(cmd.split(),stderr=STDOUT)
    logging.debug("run cmd: %s" % cmd)

def parseSubject(subject):
    info = ''
    labels = []

    cleansubj = subject.split(']')[-1][1:]
    if "PATCH" not in subject:
        return [info, cleansubj, labels]

    for i in re.findall('\[[^\[\]]+\]', subject):
        tmplist = i[1:-1].replace('PATCH', ' ').split()
        for n in tmplist:
            if '/' in n:
                info = n
            labels.append(n)

    return [info, cleansubj, labels]

def getdescfrommsg(msg):
    desc = ''
    for line in msg.splitlines():
        if line == '---':
            break

        desc += '%s\n' % line

    return desc

def genurloflist(maillist, date):
    datelist = date.split('-')
    return "%s/%s-%s/date.html" % (maillist, datelist[0], MONTH[datelist[1]])

def genurlofpatch(maillist, year, month, msgid):
    return "%s/%s-%s/msg%s.html" % (maillist, year, MONTH[str(month)], msgid)

def genurlofpatchhead(maillist, year, month):
    return "%s/%s-%s/" % (maillist, year, MONTH[str(month)])

def getmaildata(link, times=None):
    try:
        strings = urllib2.urlopen(link).read().decode("utf-8")
    except:
        logging.warning("Cannot open link: %s" % link)
        return
    return strings

def parsehtmlpatch(htmlstr, link=None, urlheader=None):
    xml = etree.HTML(htmlstr)
    try:
        lilist = xml.xpath('/html/body/ul/li')
        pre = xml.xpath('/html/body/pre')[0]
        ref = xml.xpath('/html/body/ul/li/strong')
    except:
        raise StructError("Fail to parse html")

    retpatchset = {"Follow-Ups": {}, "References": {}}

    if not lilist:
        raise ValueError, "no li element in html file"

    for i in lilist:
        if i.getchildren()[0].text == "From":
            author = i.getchildren()[0].tail[2:]
        elif i.getchildren()[0].text == "Subject":
            subject = i.getchildren()[0].tail[2:]
        elif i.getchildren()[0].text == "Date":
            date = i.getchildren()[0].tail[2:]

    if "Re:" in subject:
        raise ValueError,'cannot parse this patch'

    if '\r\n\t' in subject:
        subject = subject.replace('\r\n\t', ' ')
    if '\r\n' in subject:
        subject = subject.replace('\r\n', '')
    if '\t' in subject:
        subject = subject.replace('\t', ' ')
    msg = ''
    if pre.getchildren() == []:
        if pre.text:
            msg += pre.text
    else:
        if pre.text:
            msg += pre.text
        for n in pre.getchildren():
            if link != None:
                if "href" in n.keys():
                    for i in n.items():
                        if i[0] == "href":
                            link.append(i[1])
            if n.text:
                msg += n.text
            msg += n.tail

    """ parse sub patches """
    if urlheader != None:
        patchsetn = 0
        for n in ref:
            if n.text == "Follow-Ups":
                for m in n.getparent().xpath('./ul/li/strong/a'):
                    if "Re:" in m.text:
                        continue
                    tmpsubject = parseSubject(m.text)
                    if tmpsubject[0] != '':
                        if patchsetn == 0:
                            patchsetn = int(tmpsubject[0].split('/')[1])

                        if tmpsubject[0].split('/')[0] == '0':
                            #should not happen
                            logging.debug("%s is not the head of patchset, skip it" % subject)
                            retpatchset = {"Follow-Ups": {}, "References": {}}
                            patchsetn = 0
                            break

                    retpatchset["Follow-Ups"][tmpsubject[1]] = '%s%s' % (urlheader, m.xpath('./@href')[0])

                if len(retpatchset["Follow-Ups"]) != int(patchsetn):
                    logging.warning("patch %s: subpatch number is not equal (%d != %d)" % (subject, len(retpatchset["Follow-Ups"]), int(patchsetn)))

            if n.text == "References":
                for m in n.getparent().xpath('./ul/li/strong/a'):
                    if "Re:" in m.text:
                        continue
                    tmpsubject = parseSubject(m.text)
                    tmpsubject2 = parseSubject(subject)
                    if tmpsubject2[0] == '':
                        logging.warning("cannot get %s patch index" % subject)
                    elif int(tmpsubject2[0].split('/')[1]) == 0:
                        logging.warning("Hit a strange patch named %s" % subject)

                    retpatchset["References"][tmpsubject[1]] = '%s%s' % (urlheader, m.xpath('./@href')[0])
                    if len(retpatchset["References"]) > 1:
                        logging.warning("Hit a strange patch named %s" % subject)

    """ clean author info """
    author = author.split('<')[0]
    return [subject, author, date, msg, retpatchset]

def getinfo(msg, detail=None, subpatch=None):
    retlist = []
    patchdetail = False
    normalpatch = False
    for line in msg.splitlines():
        if line == '':
            continue

        if line[:14] == "Signed-off-by:":
            retlist.append(line[15: line.find('<') - 1])
            continue

        if line == '---':
            patchdetail = True
            continue

        if line == '--' or line == '-- ':
            break

        if patchdetail:
            if line[:10] == 'diff --git':
                normalpatch = True
                break

            if re.match('^ \S+[ ]+\|[ ]+[0-9]+ [\+\-]+$', line):
                retlist.append(line.split('|')[0].split()[0])
                if detail is not None:
                    filename = line.split('|')[0].split()[0]
                    number = line.split('|')[1].split()[0]
                    detail[filename] = int(number)
                continue
        else:
            if re.match('^ \S+[ ]+\|[ ]+[0-9]+ [\+\-]+$', line):
                retlist.append(line.split('|')[0].split()[0])
                if detail is not None:
                    filename = line.split('|')[0].split()[0]
                    number = line.split('|')[1].split()[0]
                    detail[filename] = int(number)
                continue

            tmpline = line.replace('.', '').replace(',', '').replace(':', '')
            for n in tmpline.split():
                if n != '':
                    retlist.append(n)

    if normalpatch == False and subpatch is not None:
        startparse = False
        for line in msg.splitlines():
            if re.match('^[^\(]+\([0-9]+\):$', line):
                startparse = True
                continue

            if startparse:
                if line == '':
                    startparse = False
                    continue

                if line[:3] != '   ':
                    subpatch.append(line[2:])
                else:
                    """ it is a part of last patch name"""
                    try:
                        tmpstr = subpatch.pop()
                    except IndexError:
                        """ we get a unexcept case, stop parse it """
                        logging.warning("Fail to get subpatch info")
                        subpatch = []
                        break
                    subpatch.append('%s%s' % (tmpstr, line[3:]))

    return retlist

def manualsplit(msg):
    detail = {}
    getinfo(msg, detail=detail)
    if detail == {}:
        return

    maxchange = [0, None]
    for n in detail.keys():
        if maxchange[0] < detail[n]:
            maxchange[0] = detail[n]
            maxchange[1] = n

    if maxchange[1] == None:
        return

    for n in group1:
        if n in maxchange[1]:
            return 1
    for n in group2:
        if n in maxchange[1]:
            return 2
    for n in group3:
        if n in maxchange[1]:
            return 3

def manualfilter(msg):
    detail = {}
    getinfo(msg, detail=detail)
    if detail == {}:
        return False

    for n in notsupport:
        for m in detail.keys():
            if n in m:
                return True

    return False

def savedata(filepath, data):
    f1 = file(filepath, 'wb')  
    pickle.dump(data, f1, True)
    f1.close()

def loaddata(filepath):
    f1 = file(filepath, 'rb')  
    return pickle.load(f1)

def downloadsourcecode(gitrepo):
    cmd = "git clone %s" % (gitrepo)
    try:
        output = subprocess.check_output(cmd.split(),stderr=STDOUT)
    except subprocess.CalledProcessError as detail:
        logging.warning("fail to get source code % " % gitrepo)
        return
    logging.debug("run cmd : %s" % cmd)
    return output

def getgitlog(srcdir, startdate, enddate):
    olddir = os.getcwd()
    os.chdir(srcdir)
    cmd = ['git', 'log', '--since="%s"' % startdate, '--before="%s"' % enddate, '--pretty=oneline']
    try:
        output = subprocess.check_output(cmd, stderr=STDOUT)
    except subprocess.CalledProcessError as detail:
        logging.warning("fail to get git log info")
        os.chdir(olddir)
        return
    os.chdir(olddir)
    return output

def callgitpull(srcdir):
    olddir = os.getcwd()
    os.chdir(srcdir)
    cmd = "git pull"
    try:
        output = subprocess.check_output(cmd.split(), stderr=STDOUT)
    except subprocess.CalledProcessError as detail:
        logging.warning("fail to call git pull")
        os.chdir(olddir)
        return

    os.chdir(olddir)
    return output

def testparsehtmlpatch(maillink=None):
    if maillink == None:
        maillink = "https://www.redhat.com/archives/libvir-list/2015-April/msg01484.html"
    link = []
    date = maillink.split("/")[-2]
    strings = getmaildata(maillink)
    info = parsehtmlpatch(strings, link, "http://test/")
    print info
    print ""
    print link

def loadconfig(configfile="config.yaml"):
    with open(configfile, 'r') as stream:
        return yaml.load(stream)

def pikasendmsg(server, msg, exchangename):
    """ TODO: use celery """
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=server))
    channel = connection.channel()
    channel.exchange_declare(exchange=exchangename, type='fanout')
    channel.basic_publish(exchange=exchangename, routing_key='', body=msg)
    logging.debug("Send message: %s" % msg)
    connection.close()

def jenkinsJobTrigger(parameter, job_info):
    if not job_info['url']:
        return
    data = {"token": job_info['token']}
    for key, item in job_info["parameter"].items():
        if item in parameter.keys():
            data[key] = parameter[item]
        else:
            data[key] = item

    logging.debug("Create a job on %s with parameter %s" % (job_info['url'], str(data)))
    if not job_info['verify']:
        return requests.post(job_info['url'], data=data, verify=False)
    else:
        return requests.post(job_info['url'], data=data, verify=job_info['verify'])
