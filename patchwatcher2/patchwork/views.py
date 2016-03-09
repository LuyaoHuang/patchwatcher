from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.http import JsonResponse
from django.template import RequestContext, loader
from django.forms.models import model_to_dict
from .models import Dataset
import cgi

def index(request):
    template = loader.get_template('text.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))
#    return render(request, 'text.html')

def data(request):
    ret = []
    for n in Dataset.objects.all():
        json_case = model_to_dict(n)
        json_case['date'] = json_case['date'].strftime("%Y-%m-%dT%H:%M:%S")
        json_case['name'] = cgi.escape(json_case['name']).encode('ascii', 'xmlcharrefreplace')
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
