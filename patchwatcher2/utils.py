#!/usr/bin/env python

import glob
import lxml.etree as etree
import random
import subprocess
import re
import cPickle as pickle
import os

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

def cleansubject(subject):
    if "PATCH" not in subject:
        raise ValueError, "no PATCH in subject"

    tmpstr = subject[subject.find("PATCH"):]
    cleansubj = tmpstr[tmpstr.find(']') + 2:]
    info = ''
    for n in tmpstr[:tmpstr.find(']')].split():
        if "/" in n:
            info = n
            break

    return [n, cleansubj]

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

def getmaildata(link, timeout=None):
    tmpfile = '/tmp/%s' % link.split('/')[-1]
    try:
        os.remove(tmpfile)
    except:
        pass

    if timeout is not None:
        cmd = 'wget %s -O %s --timeout=%s' % (link, tmpfile, timeout)
    else:
        cmd = 'wget %s -O %s' % (link, tmpfile)

    try:
        subprocess.check_output(cmd.split())
    except:
        if timeout is not None:
            if timeout > 600:
                raise ValueError, "cannot get %s" % link
            return getmaildata(link, timeout=timeout+60)
        else:
            return getmaildata(link, 60)

    f = open(tmpfile)
    ret = f.read()
    f.close()
    os.remove(tmpfile)
    return ret

def parsehtmlpatch(htmlstr):
    xml = etree.HTML(htmlstr)
    lilist = xml.xpath('/html/body/ul/li')
    pre = xml.xpath('/html/body/pre')[0]

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
        msg += pre.text
    else:
        msg += pre.text
        for n in pre.getchildren():
            msg += n.tail

    author = author.split('<')[0]
    return [subject, author, date, msg]

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
                    tmpstr = subpatch.pop()
                    subpatch.append('%s%s' % (tmpstr, line[3:]))

    return retlist

def manualsplit(msg):
    detail = {}
    getinfo(msg, detail)
    if detail == {}:
        return

    maxchange = [0, None]
    for n in detail.keys():
        if maxchange[0] < detail[n]:
            maxchange[0] = detail[n]
            maxchange[1] = n

    if maxchange[1] == None:
        print detail
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
    getinfo(msg, detail)
    if detail == {}:
        return False

    maxchange = [0, None]
    for n in detail.keys():
        if maxchange[0] < detail[n]:
            maxchange[0] = detail[n]
            maxchange[1] = n

    if maxchange[1] == None:
        print detail
        return False

    for n in notsupport:
        if n in maxchange[1]:
            return True

    return False

def savedata(filepath, data):
    f1 = file(filepath, 'wb')  
    pickle.dump(data, f1, True)
    f1.close()

def loaddata(filepath):
    f1 = file(filepath, 'rb')  
    return pickle.load(f1)

