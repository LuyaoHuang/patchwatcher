"""patchwatcher2 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from patchwork import views
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', views.index, name='text'),
    url(r'^data$', views.data, name='data'),
    url(r'^updategroup$', views.updategroup, name='updategroup'),
    url(r'^updatetestcase$', views.updatetestcase, name='updatetestcase'),
    url(r'^updatetestby$', views.updatetestby, name='updatetestby'),
    url(r'^updatestate$', views.updatestate, name='updatestate'),
    url(r'^updatecomment$', views.updatecomment, name='updatecomment'),
    url(r'^updatepushed$', views.updatepushed, name='updatepushed'),
    url(r'^updatetestplan$', views.updatetestplan, name='updatetestplan'),
    url(r'^updatefeature$', views.updatefeature, name='updatefeature'),
    url(r'^updatebuglink$', views.updatebuglink, name='updatebuglink'),
    url(r'^patchfile/([0-9a-f]{32})$', views.creatpatchfile, name='creatpatchfile'),
    url(r'^showallmd5lable$', views.showallmd5lable, name='showallmd5lable'),
]
