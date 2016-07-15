from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Dataset(models.Model):
    name = models.CharField(max_length=100)
    desc = models.CharField(max_length=65536)
    group = models.CharField(max_length=10)
    patchlink = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    date = models.DateTimeField()
    testcase = models.CharField(max_length=100, default="N/A" ,blank=True, null=True)
    testby = models.CharField(max_length=100, default="" ,blank=True, null=True)
    state = models.CharField(max_length=100, default="ToDo")
    comment = models.CharField(max_length=65536, default="" ,blank=True, null=True)
    pushed = models.CharField(max_length=10, default="No" ,blank=True, null=True)
    testplan = models.CharField(max_length=10, default="ToDo" ,blank=True, null=True)
    feature = models.CharField(max_length=100, default="" ,blank=True, null=True)
    buglink = models.CharField(max_length=100, default="N/A" ,blank=True, null=True)

    md5lable = models.CharField(max_length=10, default="" ,blank=True, null=True)
    patchlabel = models.CharField(max_length=100, default="" ,blank=True, null=True)

    subpatch = models.ManyToManyField("self")

class currentwork(models.Model):
    date = models.CharField(max_length=10)
    msgid = models.CharField(max_length=10)

class Patchinfos(models.Model):
    startdate = models.DateTimeField()
    enddate = models.DateTimeField()
