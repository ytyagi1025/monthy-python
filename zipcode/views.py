from django.shortcuts import render
import json, itertools, datetime
from django.http import HttpResponseRedirect
from django.http import HttpRequest, HttpResponse
from django.http import JsonResponse
from zipcode.models import *
from zipcode.forms import *
from django.core.mail import send_mail
from zipcode.calendars import *
from django.views.generic.detail import DetailView
from django.core import serializers
from django.core.context_processors import csrf
from django.core.mail import send_mail
from django.template.loader import render_to_string


def day_or_night():
    if datetime.datetime.now().time().hour < 17:
        time_image = 'day'
    else:
        time_image = 'night'
    return time_image


def home(request):
    time_image = day_or_night()
    testimonials = Testimonial.objects.filter(best_of=True)
    monthly_specials = MonthlySpecial.objects.filter(special_active=True)
    return render(request, 'home.html', {'time_image': time_image, 'testimonials': testimonials, 'monthly_specials': monthly_specials})


def monthly_special_detail(request, id, special):
    time_image = day_or_night()
    monthly_special = MonthlySpecial.objects.get(id = id)
    return render(request, 'monthly_special_detail.html', {'monthly_special': monthly_special, 'time_image': time_image})


def results(request, postcode):
    con = Contractor.objects.filter(areacode=postcode).prefetch_related().order_by("lastname")
    time_image = day_or_night()
    return render(request, 'results.html', {'con': con, 'time_image': time_image})


def get_zip(request):
    if request.method == 'POST':
        form = ZipForm(request.POST)
        if form.is_valid():
            c = Contractor.objects.filter(areacode=request.POST['zipsearch'])
            contractor = ""
            for i in c:
                contractor += '/'+ i.firstname +'/'+  str(i.id) +'/'+ i.lastname
            return HttpResponseRedirect(str(contractor))
            #return HttpResponseRedirect('/search/' + request.POST['zipsearch'])
    else:
        form = ZipForm()
    return render(request, 'search.html', {'form': form})


def get_contact(request):
    if request.method == 'POST':
        contactform = ContactForm(request.POST)
        if contactform.is_valid():
            message = "{name} / {address} / {email} said: ".format(
                    name=contactform.cleaned_data.get('name'),
                        address=contactform.cleaned_data.get('address'),
                        email=contactform.cleaned_data.get('email'))
            message += "\n\n{0}".format(contactform.cleaned_data.get('problem'))
            send_mail(
                subject=contactform.cleaned_data.get('name').strip(),
                    message=message,
                    from_email='wbeyda@gmail.com',
                    recipient_list=['wbeyda@gmail.com'],
            )
            return HttpResponseRedirect('/thanks/')
    else:
            contactform = ContactForm(auto_id="contact_%s")
    return render(request, 'contact.html', {'contactform': contactform})


def post_testimonial(request, id):
    if request.method == 'POST':
        testimonial_form = TestimonialForm(request.POST,request.FILES)
        if testimonial_form.is_valid():
            newform = testimonial_form.save(commit=False)
            newform.contractor_id = id
            newform.approved_status = False
            newform.save()
            print("this posted")
            return HttpResponseRedirect('/thanks/')
        else:
            testimonial_form = TestimonialForm()
            return HttpResponse('error')

def request_event(request, id, month=None, day=None, year=None, hour=None):
    if request.method == 'POST':
        try:
            cust = Customer.objects.get(phone_number = request.POST['customer'])
        except Customer.DoesNotExist as e:
            customer_error = {'error': str(e)}
            return JsonResponse(data=customer_error)
        data = request.POST.copy()
        data['customer'] = cust.pk
        requested_event = ContractorScheduleForm(data)
    elif request.method == 'GET':
        start_date = datetime.datetime(int(request.GET['year']),int(request.GET['month']),int(request.GET['day']),int(request.GET['hour'])) 
        requested_event = ContractorScheduleForm(initial = {'start_date': start_date})
        return render(request, 'request_event.html', {'requested_event':requested_event})
    if requested_event.errors:
        errors = {f: e.get_json_data() for f, e in requested_event.errors.items()}
        errors['success'] = False
        return JsonResponse(data=errors)
    elif requested_event.is_valid():
        requested_event.save(commit=False)
        requested_event.firstname_id = id
        requested_event.save()
        job = requested_event.save()
        contractor_subject = "You have a new job request!"
        contractor_message = "you have a new job request for job number " + str(job.pk)
        contractor_from    = "admin@athomehero.net"
        contractor_email      = job.firstname.user.email
        send_mail(contractor_subject, contractor_message, contractor_from,
                 [contractor_email], fail_silently = False, html_message= render_to_string('zipcode/thanks.html'))

        customer_subject = "At home Services Job Request Submission For Job Number" + str(job.id)
        customer_message = "Thanks for requesting this job"
        customer_to = job.customer.email
        send_mail(customer_subject, customer_message, contractor_email,
                 [customer_to], fail_silently = False, html_message=render_to_string('zipcode/thanks.html'))
        thanks = {"success": True, "customer_name": job.customer.first_name, "customer_email": job.customer.email}
        return JsonResponse(data=thanks)

def validate_file_extension(value):
    import os
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf','.doc','.docx']
    if not ext in valid_extensions:
        raise ValidationError(u'File not supported!')


def handle_uploaded_file(f):
    with open(f, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def get_resume(request):
    if request.method == 'POST':
        careerform = CareerForm(request.POST, request.FILES)
        if careerform.is_valid():
            careerform.save()
            return HttpResponseRedirect('/thanks')
        else:
            careerform = CareerForm()
        return render(request, 'careers.html', {'careerform':careerform})
    else:
        careerform = CareerForm()
    time_image = day_or_night
    return render(request, 'careers.html', {'careerform':careerform, 'time_image': time_image})


def show_gallery(request):
    gallery = Gallery.objects.filter(testimonial__approved_status = True, testimonial__best_of = True)
    time_image = day_or_night()
    return render(request, 'gallery.html', {'gallery':gallery,'time_image': time_image})


def calendar_manager_cells(request,  currentyear, currentmonth, uid):
    fdom = datetime.datetime(int(currentyear), int(currentmonth), 1,0)

    if int(currentmonth) == 12:
        ldom = datetime.datetime(int(currentyear)+1,1,1,0)
    else:
        ldom = datetime.datetime(int(currentyear),int(currentmonth)+1,1,0)
    import calendar
    month_range = calendar.monthrange(int(currentyear),int(currentmonth))[1]

    avail = Availability.objects.get(contractor_id=int(uid))
    length_of_hours = len(range(avail.prefered_starting_hours.hour, avail.prefered_ending_hours.hour+1))
    full_days = []
    for i in range(1,month_range+1):
        full_day = calendar_manager_blocks(request,i, uid, currentyear, currentmonth)
        if type(full_day) == HttpResponse:
            full_day = json.loads(full_day.content)
        if len(full_day) == length_of_hours:
            full_days.append(i)
    if request.is_ajax():
        full_days_json = json.dumps(full_days)
        return HttpResponse(full_days_json)
    else:
        return full_days

    """
    cal_query = ContractorSchedule.objects.filter(firstname_id =int(uid), start_date__gte = fdom, end_date__lt = ldom)
    av = Availability.objects.get(contractor_id=int(uid))
    sh = av.prefered_starting_hours
    eh = av.prefered_ending_hours
    ah = datetime.datetime.combine(date.today(), eh) - datetime.datetime.combine(date.today(), sh)
    avail_hours = ah.total_seconds() / 3600 #8.0 or 8.5
    alldays = cal_query.filter(all_day = True)
    full_days = []

    for i in alldays: #if the first day of a chunk starts at the begining of Availability add it to full days in full_days
        full_days.append(range(i.start_date.day, i.end_date.day))
    full_days_in_this_month = sum(full_days, [])

    #this is where comments started

        if chunk_of_days > 0:
            psh = datetime.datetime.combine(i.start_date, sh)
        if psh == i.start_date:
            full_days.append(i.start_date.day)

    for i in chunk_of_days[1:]: #add the rest of the days from a chunk to full_days
        full_days.append(i)

    for i in cal_query:
        full_days.append(i.start_date.day)

    a = [elem for elem in full_days if elem >= avail_hours /2]
    full_days_in_this_month = []
    [full_days_in_this_month.append(item) for item in a if item not in full_days_in_this_month]

    if request.is_ajax():
        full_days_json = json.dumps(full_days_in_this_month)
        return HttpResponse(full_days_json)
    else:
        return full_days_in_this_month
    """


def next_month_request(request, id, currentyear, currentmonth):
    if request.is_ajax():
        if int(request.GET.get('currentmonth')) == 12:
            nextyear = int(request.GET.get('currentyear')) + 1
            qs = ContractorSchedule.objects.filter(firstname_id=int(id)).exclude(
                                                                            start_date__lt=datetime.datetime(
                                                                                int(currentyear),
                                                                                int(currentmonth),
                                                                                1)
                                                                        ).exclude(
                                                                        start_date__gt=datetime.datetime(nextyear,1,31,23,59,59))
            queryset = []
            for i in qs:
                h,m =  i.start_date.hour, i.start_date.minute
                if i.start_date.month != i.end_date.month:
                    i.start_date = last_day_of_month(i.start_date) + datetime.timedelta(seconds=1)+ datetime.timedelta(hours=h) + datetime.timedelta(minutes=m)
                    queryset.append(i)
                else:
                    queryset.append(i)
            if queryset:
                htmlcalendar = next_last_month_contractor_calendar(queryset)
                return HttpResponse(htmlcalendar)
            else:
                htmlcalendar = LocaleHTMLCalendar().formatmonth(nextyear,1)
                return HttpResponse(htmlcalendar)
        elif int(request.GET.get('currentmonth')) != 12 :
            cid = int(request.GET.get("id"))
            nextmonth = int(request.GET.get('currentmonth')) +1
            cy = int(request.GET.get('currentyear'))
            d = datetime.datetime(cy,nextmonth,1)
            qs = ContractorSchedule.objects.filter(firstname_id=cid).exclude(
                          start_date__lt=first_day_of_month(datetime.datetime(cy,int(currentmonth),1))).exclude(
                          start_date__gt=last_day_of_month(d))
            queryset = []
            for i in qs:
                #import pdb; pdb.set_trace()
                h,m =  i.start_date.hour, i.start_date.minute
                if i.start_date.month < i.end_date.month and i.end_date.month == nextmonth:
                    i.start_date = last_day_of_month(i.start_date) + datetime.timedelta(seconds=1)+ datetime.timedelta(hours=h) + datetime.timedelta(minutes=m)
                    queryset.append(i)
                elif i.start_date.month == nextmonth:
                    queryset.append(i)
            if not queryset:
                htmlcalendar = LocaleHTMLCalendar().formatmonth(cy,nextmonth)
            else:
                htmlcalendar = next_last_month_contractor_calendar(queryset)
        return HttpResponse(htmlcalendar)

def last_month_request(request, id, currentyear, currentmonth):
    if request.is_ajax():
        if int(request.GET.get("currentmonth")) == 1:
            lastyear = int(currentyear) -1
            qs = ContractorSchedule.objects.filter(firstname_id=int(request.GET.get("id"))).exclude(
                        start_date__gt=datetime.datetime(lastyear,12,31,23,59,59)).exclude(
                        end_date__lt=datetime.datetime(lastyear,11,1)
                      )
            queryset = []
            for i in qs:
                h,m = i.start_date.hour, i.start_date.minute
                if i.end_date.month == 12 and i.start_date.month <= 12:
                    i.start_date = datetime.datetime(lastyear,12,1) + datetime.timedelta(hours=h) + datetime.timedelta(minutes=m)
                    queryset.append(i)
                else:
                    queryset.append(i)
            if not queryset:
                htmlcalendar = LocaleHTMLCalendar().formatmonth(lastyear, 12)
                return HttpResponse(htmlcalendar)
            else:
                htmlcalendar = next_last_month_contractor_calendar(queryset)
                return HttpResponse(htmlcalendar)
        elif int(request.GET.get("currentmonth")) != 1:
            lastmonth = int(request.GET.get("currentmonth")) -1
            cy = int(currentyear)
            d = datetime.datetime(cy,lastmonth,1)
            qs = ContractorSchedule.objects.filter(firstname_id=int(id)).exclude(
                           start_date__gt = last_day_of_month(d)).exclude(
                           end_date__lt = d)
            queryset = []

            for i in qs:
                h,m = i.start_date.hour, i.start_date.minute
                if i.end_date.month == lastmonth and i.start_date.month < lastmonth:
                    i.start_date = last_day_of_month(i.start_date) + datetime.timedelta(seconds=1)+ datetime.timedelta(hours=h) + datetime.timedelta(minutes=m)
                    queryset.append(i)
                elif i.start_date.month == lastmonth:
                    queryset.append(i)
            if not queryset:
                htmlcalendar = LocaleHTMLCalendar().formatmonth(cy,lastmonth)
                return HttpResponse(htmlcalendar)
            else:
                htmlcalendar = next_last_month_contractor_calendar(queryset)
                return HttpResponse(htmlcalendar)


def calendar_manager_blocks(request, currentdate, uid, currentyear, currentmonth):

    #import pdb; pdb.set_trace()
    today = datetime.datetime(int(currentyear),int( currentmonth), int(currentdate), 0)
    import calendar
    last_day_of_month  = calendar.monthrange(int(currentyear), int(currentmonth))[1]
    if int(currentdate) == last_day_of_month and int(currentmonth) == 12:
        tomorrow = datetime.datetime(int(currentyear)+1, 1,1,0)
    elif int(currentdate) == last_day_of_month and int(currentmonth) <= 11:
        tomorrow = datetime.datetime(int(currentyear), int(currentmonth)+1, 1, 0)
    else:
        tomorrow = datetime.datetime(int(currentyear), int(currentmonth), int(currentdate)+1, 0)
    uid = int(uid)
    all_the_days = []

    #import pdb; pdb.set_trace()

    qs = ContractorSchedule.objects.filter(firstname_id = uid)
    days_that_end_today = qs.filter(end_date__lte=tomorrow, end_date__gte=today)
    days_that_start_today = qs.filter(start_date__lte=tomorrow, start_date__gte=today)
    in_the_middle_of_a_block = qs.filter(start_date__lte=today, end_date__gte=tomorrow)

    from itertools import chain
    result_list = list(chain(days_that_end_today, days_that_start_today, in_the_middle_of_a_block))
    result_list = set(result_list)          #remove any duplicates
    all_the_hours = []

    avail = Availability.objects.get(id=uid)
    for i in result_list:
        if i.start_date.day == i.end_date.day:                                #normal days
            hourly_range = range(i.start_date.hour,i.end_date.hour+1)
        elif i.start_date.day < today.day and i.end_date.day >= tomorrow.day:  #in the middle of a block
            hourly_range = range(avail.prefered_starting_hours.hour, avail.prefered_ending_hours.hour+1)
        elif i.start_date.day < today.day:                                    # started before today
            hourly_range = range(avail.prefered_starting_hours.hour, i.end_date.hour+1)
        elif i.start_date.day < i.end_date.day:                               # starts today but ends after 
            hourly_range = range(i.start_date.hour, avail.prefered_ending_hours.hour+1)
        all_the_hours.append(hourly_range)

    all_the_hours = sum(all_the_hours,[])
    s = avail.prefered_starting_hours.hour
    e = avail.prefered_ending_hours.hour
    all_the_hours =[h for h in all_the_hours if h in range(s, e+1)]
    data = json.dumps(sorted(set(all_the_hours))) #remove duplicates and sort for clarity

    if request.is_ajax():
        return HttpResponse(data, content_type="application/json")
    else:
        return sorted(set(all_the_hours))


        """
        for i in all_the_hours:
            if i < avail.prefered_starting_hours.hour:
                all_the_hours.remove(i)
            if i > avail.prefered_ending_hours.hour:
                all_the_hours.remove(i)

        calendardays = ContractorSchedule.objects.filter(firstname_id=uid,
                                                         start_date__gte = today,
                                                         end_date__lt = tomorrow
                                                        ).order_by('start_date')

        first_day_of_chunks_of_days = ContractorSchedule.objects.filter(firstname_id = uid,
                                                           start_date__gte = today,
                                                           all_day = True,
                                                           start_date__lte = tomorrow
                                                           ).order_by('start_date')

        middle_of_a_chunk_of_days = ContractorSchedule.objects.filter(firstname_id = uid,
                                                                      start_date__lte = today,
                                                                      end_date__gte = tomorrow,
                                                                      all_day = True,
                                                                     ).order_by('start_date')

        end_of_a_chunk_of_days = ContractorSchedule.objects.filter(firstname_id = uid,
                                                                   end_date__gte = today,
                                                                   end_date__lte = tomorrow,
                                                                   all_day = True,
                                                                  ).order_by('start_date')


        if first_day_of_chunks_of_days.exists():
           all_the_days.append(first_day_of_chunks_of_days)
        else :
            first_day = ""
            all_the_days.append(first_day)

        if middle_of_a_chunk_of_days.exists():
            all_the_days.append(middle_of_a_chunk_of_days)
        else:
            middle = ""
            all_the_days.append(middle)

        if end_of_a_chunk_of_days.exists():
            all_the_days.append( end_of_a_chunk_of_days)
        else:
            end = ""
            all_the_days.append( end)

        if calendardays.exists():
            all_the_days.append(calendardays)
        else:
            caldays = ""
            all_the_days.append( caldays )

        filtered_days = [elem for elem in all_the_days if elem != ""]
        all_days = list(itertools.chain(filtered_days[0]))
        data = serializers.serialize('json', all_days, use_natural_keys=True )
        return HttpResponse(data, content_type="application/json")
        """

def contractor_detail_view(request, f,id,l):
    con = Contractor.objects.filter(id=id).prefetch_related()
    avail = Availability.objects.filter(contractor_id=id).prefetch_related()
    avail = serializers.serialize("json", avail)
    testimonials = Testimonial.objects.filter(contractor_id=id, approved_status = True).prefetch_related()
    htmlcalendar = contractor_calendar(con)
    from django.forms.models import inlineformset_factory
    conschedule = ContractorSchedule.objects.filter(firstname_id=id)
    testimonial_form = testimonialform_factory(conschedule)
    time_image = day_or_night()
    monthly_specials = MonthlySpecial.objects.filter(special_active=True)
    cal_man_cells = calendar_manager_cells(request, datetime.datetime.today().year, datetime.datetime.today().month, id)

    return render(request, 'contractor_detail.html', {'con': con,
                                                      'htmlcalendar': htmlcalendar,
                                                      'testimonials': testimonials,
                                                      'testimonial_form': testimonial_form,
                                                      'availability': avail,
                                                      'time_image': time_image,
                                                      'monthly_specials': monthly_specials,
                                                      'cal_man_cells': cal_man_cells
                                                      })

def customer_create(request):
    if request.method == 'POST':
        customer = CustomerForm(request.POST)
        if customer.is_valid():
            customer.save()
            thanks = {'thanks': "Thanks for joining us!"}
            return JsonResponse(data=thanks)
    else:
        customer = CustomerForm()
    return render(request, 'customer_create.html', {'customer': customer})
