from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Dataset(models.Model):
    name = models.CharField(max_length=100)
    desc = models.CharField(max_length=65536)
    group = models.CharField(max_length=10)
    patchlink = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    date = models.CharField(max_length=100)
    testcase = models.CharField(max_length=100)
    testby = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

class currentwork(models.Model):
    date = models.CharField(max_length=10)
    msgid = models.CharField(max_length=10)
