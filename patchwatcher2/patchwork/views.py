from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.http import JsonResponse
from django.template import RequestContext, loader
from django.forms.models import model_to_dict
from .models import Dataset
import cgi
from patchwork import createpatch, create_patch_set
from django.db.models import Q

def index(request):
    template = loader.get_template('text.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context), content_type="charset=utf-8")

def data(request):
    ret = []
    for n in Dataset.objects.all():
        if len(n.subpatch.all()) == 1:
            continue
        json_case = model_to_dict(n)
        json_case['date'] = json_case['date'].strftime("%Y-%m-%dT%H:%M:%S")
        json_case['name'] = cgi.escape(json_case['name']).encode('ascii', 'xmlcharrefreplace')
        json_case['desc'] = cgi.escape(json_case['desc']).encode('ascii', 'xmlcharrefreplace')

        if len(n.subpatch.all()) > 1:
            patchlist = []
            allpushed = True
            for m in n.subpatch.all():
                patchlist.append({'name': m.name,
                                  'patchlink': m.patchlink,
                                  'pushed': m.pushed})
                if m.pushed == 'No':
                    allpushed = False

            json_case['subpatch'] = patchlist
            if allpushed:
                json_case['pushed'] = 'Yes'

        ret.append(json_case)

    return JsonResponse({'data': ret})

def updategroup(request):
    link = request.POST.get('link')
    newgroup = request.POST.get('newgroup')
    oldgroup = request.POST.get('oldgroup')

    data = Dataset.objects.get(patchlink=link)
    if data.group != oldgroup:
        return JsonResponse({'ret': 1})
    else:
        data.group = newgroup
        data.save()

    return JsonResponse({'ret': 0})

def updatetestcase(request):
    link = request.POST.get('link')
    newtestcase = request.POST.get('newtestcase')
    oldtestcase = request.POST.get('oldtestcase')

    data = Dataset.objects.get(patchlink=link)
    if data.testcase != oldtestcase:
        return JsonResponse({'ret': 1})
    else:
        data.testcase = newtestcase
        data.save()

    return JsonResponse({'ret': 0})

def updatetestby(request):
    link = request.POST.get('link')
    newtestby = request.POST.get('newtestby')
    oldtestby = request.POST.get('oldtestby')

    data = Dataset.objects.get(patchlink=link)
    if data.testby != oldtestby:
        return JsonResponse({'ret': 1})
    else:
        data.testby = newtestby
        data.save()

    return JsonResponse({'ret': 0})

def updatestate(request):
    link = request.POST.get('link')
    newstate = request.POST.get('newstate')
    oldstate = request.POST.get('oldstate')

    data = Dataset.objects.get(patchlink=link)
    if data.state != oldstate:
        return JsonResponse({'ret': 1})
    else:
        data.state = newstate
        data.save()

    return JsonResponse({'ret': 0})

def updatecomment(request):
    link = request.POST.get('link')
    newcom = request.POST.get('newcomment')
    oldcom = request.POST.get('oldcomment')

    data = Dataset.objects.get(patchlink=link)
    data.comment = newcom
    data.save()

    return JsonResponse({'ret': 0})

def updatepushed(request):
    link = request.POST.get('link')
    newpushed = request.POST.get('newpushed')
    oldpushed = request.POST.get('oldpushed')

    data = Dataset.objects.get(patchlink=link)
    if data.pushed != oldpushed:
        return JsonResponse({'ret': 1})
    else:
        data.pushed = newpushed
        data.save()

    return JsonResponse({'ret': 0})

def updatetestplan(request):
    link = request.POST.get('link')
    newtestplan = request.POST.get('newtestplan')
    oldtestplan = request.POST.get('oldtestplan')

    data = Dataset.objects.get(patchlink=link)
    if data.testplan != oldtestplan:
        return JsonResponse({'ret': 1})
    else:
        data.testplan = newtestplan
        data.save()

    return JsonResponse({'ret': 0})

def updatefeature(request):
    link = request.POST.get('link')
    newfeature = request.POST.get('newfeature')
    oldfeature = request.POST.get('oldfeature')

    data = Dataset.objects.get(patchlink=link)
    if data.feature != oldfeature:
        return JsonResponse({'ret': 1})
    else:
        data.feature = newfeature
        data.save()

    return JsonResponse({'ret': 0})

def updatebuglink(request):
    link = request.POST.get('link')
    newbuglink = request.POST.get('newbuglink')
    oldbuglink = request.POST.get('oldbuglink')

    data = Dataset.objects.get(patchlink=link)
    if data.buglink != oldbuglink:
        return JsonResponse({'ret': 1})
    else:
        data.buglink = newbuglink
        data.save()

    return JsonResponse({'ret': 0})

def creatpatchfile(request, md5code):
    try:
        data = Dataset.objects.get(md5lable=md5code)
    except:
        return HttpResponse("Error", content_type="text/plain; charset=utf-8")

    if len(data.subpatch.all()) > 1:
        patch = create_patch_set([i.patchlink for i in data.subpatch.all()])

    elif len(data.subpatch.all()) == 1 and data.subpatch.all()[0].patchlink != data.patchlink:
        try:
            patch, _ = createpatch(data.patchlink)
        except:
            patch, _ = createpatch(data.subpatch.all()[0].patchlink)
    else:
        patch, _ = createpatch(data.patchlink)

    return HttpResponse(patch, content_type="text/plain; charset=utf-8")

def showallmd5lable(request):
    retdict = {}
    objs = Dataset.objects.filter(~Q(md5lable=""))
    for i in objs:
        retdict[i.patchlink] = i.md5lable

    return JsonResponse(retdict)
