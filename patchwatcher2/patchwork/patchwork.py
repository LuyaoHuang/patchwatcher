import os
import lxml.etree as etree
import subprocess
import urllib2

""" TODO: move patchwatcher in this dir """
def patchsequence(patchlinklist):
    patchbase = patchlinklist[0][:patchlinklist[0].find("msg")]
    tmpdict = {}
    for i in patchlinklist:
        if patchbase not in i:
            raise Exception("One of these patch link is not right")

        tmpdict[i[i.find("msg")+3:-5]] = i

    tmplist = tmpdict.keys()
    tmplist.sort()
    return [tmpdict[i] for i in tmplist]

def improvemailaddr(strings):
    if '<' in strings and '>' in strings:
        tmplist = strings[strings.find('<')+1:strings.find('>')].split()
        retstrings = "%s@" % tmplist[0]
        first = 0
        for n in tmplist[1:]:
            if first == 0:
                first = 1
                retstrings += n
            else:
                retstrings += '.%s' % n

        return '%s <%s>' % (strings[:strings.find('<')], retstrings)

def createpatch(htmllink):
    returnstr = ""
    strings = urllib2.urlopen(htmllink).read().decode("utf-8")
    xml = etree.HTML(strings)

    try:
        lilist = xml.xpath('/html/body/ul/li')
        pre = xml.xpath('/html/body/pre')[0]
    except:
        raise Exception("Fail to parse html")

    for i in lilist:
        if i.getchildren()[0].text == "From":
            author = i.getchildren()[0].tail[2:]
        elif i.getchildren()[0].text == "Subject":
            subject = i.getchildren()[0].tail[2:]
        elif i.getchildren()[0].text == "Date":
            date = i.getchildren()[0].tail[2:]

    tmpstr = improvemailaddr(author)

    if '\r\n\t' in subject:
        subject = subject.replace('\r\n\t', ' ')
    if '\r\n' in subject:
        subject = subject.replace('\r\n', '')
    if '\t' in subject:
        subject = subject.replace('\t', ' ')

    returnstr += 'From: %s\n' % tmpstr
    returnstr += 'Date: %s\n' % date
    returnstr += 'Subject: %s\n\n' % subject

    if pre.getchildren() == []:
        if pre.text:
            returnstr += pre.text
    else:
        if pre.text:
            returnstr += pre.text
        for n in pre.getchildren():
            if n.text:
                returnstr += n.text
            returnstr += n.tail

    if "diff --git" not in returnstr:
        raise Exception("this is not a patch!")

    return returnstr

if __name__ == '__main__':

    print createpatch("https://www.redhat.com/archives/libvir-list/2016-June/msg01022.html")
