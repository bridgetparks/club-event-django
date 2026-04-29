from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView
from .forms import ClubForm, GonzagaSignUpForm, MembershipForm, EventForm
from .models import Attendance, Club, ClubMembership, Event, EventRSVP

class SignUpView(CreateView):
    form_class = GonzagaSignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, 'Welcome! Your Gonzaga account is ready.')
        return response


def manageable_clubs(user):
    if user.is_superuser:
        return Club.objects.all()
    return Club.objects.filter(leaders__user=user)


def user_can_manage_club(user, club):
    return user.is_superuser or club.leaders.filter(user=user).exists()


@login_required
def dashboard(request):
    context = {
        'student_count': User.objects.count(),
        'club_count': Club.objects.count(),
        'membership_count': ClubMembership.objects.count(),
        'event_count': Event.objects.count(),
        'recent_memberships': ClubMembership.objects.select_related('user', 'club').order_by('-joined_at')[:8],
        'upcoming_events': Event.objects.prefetch_related('clubs', 'tags').filter(event_date__gte=timezone.now()).order_by('event_date')[:8],
    }
    return render(request, 'clubs/dashboard.html', context)


@login_required
def club_list(request):
    clubs = Club.objects.annotate(member_total=Count('memberships')).prefetch_related('leaders__user')
    return render(request, 'clubs/club_list.html', {'clubs': clubs})


@login_required
def club_detail(request, pk):
    club = get_object_or_404(Club, pk=pk)
    roster = club.memberships.select_related('user').order_by('user__last_name', 'user__first_name')
    events = club.events.order_by('event_date')
    return render(request, 'clubs/club_detail.html', {'club': club, 'roster': roster, 'events': events, 'can_manage': user_can_manage_club(request.user, club)})


@login_required
def club_create(request):
    if not request.user.is_superuser:
        messages.error(request, 'Only admins can create clubs.')
        return redirect('club_list')
    form = ClubForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, 'Club created.'); return redirect('club_list')
    return render(request, 'clubs/form.html', {'form': form, 'title': 'Create Club'})


@login_required
def club_update(request, pk):
    club = get_object_or_404(Club, pk=pk)
    if not user_can_manage_club(request.user, club):
        messages.error(request, 'You do not manage this club.')
        return redirect('club_detail', pk=club.pk)
    form = ClubForm(request.POST or None, instance=club)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, 'Club updated.'); return redirect('club_detail', pk=club.pk)
    return render(request, 'clubs/form.html', {'form': form, 'title': 'Edit Club'})


@login_required
def club_delete(request, pk):
    club = get_object_or_404(Club, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, 'Only admins can delete clubs.')
        return redirect('club_detail', pk=club.pk)
    if request.method == 'POST':
        club.delete(); messages.success(request, 'Club deleted.'); return redirect('club_list')
    return render(request, 'clubs/confirm_delete.html', {'object': club, 'title': 'Delete Club'})


@login_required
def membership_list(request):
    club_id = request.GET.get('club')
    memberships = ClubMembership.objects.select_related('user', 'club')
    if club_id:
        memberships = memberships.filter(club_id=club_id)
    return render(request, 'clubs/membership_list.html', {'memberships': memberships, 'clubs': Club.objects.all(), 'selected_club': club_id})


@login_required
def membership_add(request):
    if not (request.user.is_superuser or request.user.club_leaderships.exists()):
        messages.error(request, 'Only admins and club leaders can enroll students.')
        return redirect('membership_list')
    form = MembershipForm(request.POST or None)
    if not request.user.is_superuser:
        form.fields['club'].queryset = manageable_clubs(request.user)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, 'Student enrolled.'); return redirect('membership_list')
    return render(request, 'clubs/form.html', {'form': form, 'title': 'Enroll Student'})


@login_required
def membership_remove(request, pk):
    membership = get_object_or_404(ClubMembership, pk=pk)
    if not user_can_manage_club(request.user, membership.club):
        messages.error(request, 'You do not manage this club.')
        return redirect('membership_list')
    if request.method == 'POST':
        membership.delete(); messages.success(request, 'Membership removed.'); return redirect('membership_list')
    return render(request, 'clubs/confirm_delete.html', {'object': membership, 'title': 'Remove Membership'})


@login_required
def event_list(request):
    events = Event.objects.select_related('category').prefetch_related('clubs', 'tags').order_by('event_date')
    category = request.GET.get('category')
    tag = request.GET.get('tag')
    if category:
        events = events.filter(category_id=category)
    if tag:
        events = events.filter(tags__id=tag)
    return render(request, 'clubs/event_list.html', {'events': events.distinct()})


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event.objects.prefetch_related('clubs', 'tags'), pk=pk)
    rsvp = EventRSVP.objects.filter(event=event, user=request.user).first()
    return render(request, 'clubs/event_detail.html', {'event': event, 'rsvp': rsvp, 'can_manage': event.user_can_manage(request.user)})


@login_required
def event_create(request):
    clubs = manageable_clubs(request.user)
    if not (request.user.is_superuser or clubs.exists()):
        messages.error(request, 'Only admins and club leaders can create events.')
        return redirect('event_list')
    form = EventForm(request.POST or None, request.FILES or None, manageable_clubs=clubs)
    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.created_by = request.user
        event.save()
        form.save_m2m()
        form.save_tags(event)
        messages.success(request, 'Event created.')
        return redirect('event_detail', pk=event.pk)
    return render(request, 'clubs/form.html', {'form': form, 'title': 'Create Event', 'multipart': True})


@login_required
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not event.user_can_manage(request.user):
        messages.error(request, 'You do not manage this event.')
        return redirect('event_detail', pk=pk)
    form = EventForm(request.POST or None, request.FILES or None, instance=event, manageable_clubs=manageable_clubs(request.user))
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, 'Event updated.'); return redirect('event_detail', pk=pk)
    return render(request, 'clubs/form.html', {'form': form, 'title': 'Edit Event', 'multipart': True})


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not event.user_can_manage(request.user):
        messages.error(request, 'You do not manage this event.')
        return redirect('event_detail', pk=pk)
    if request.method == 'POST':
        event.delete(); messages.success(request, 'Event deleted.'); return redirect('event_list')
    return render(request, 'clubs/confirm_delete.html', {'object': event, 'title': 'Delete Event'})


@login_required
def event_rsvp(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        rsvp = event.rsvp_user(request.user)
        messages.success(request, 'You are on the waitlist.' if rsvp.status == EventRSVP.Status.WAITLISTED else 'You are going!')
    return redirect('event_detail', pk=pk)


@login_required
def event_cancel_rsvp(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        rsvp = EventRSVP.objects.filter(event=event, user=request.user).first()
        if rsvp:
            rsvp.status = EventRSVP.Status.CANCELLED
            rsvp.save(update_fields=['status', 'updated_at'])
            event.promote_waitlist()
            messages.success(request, 'Your RSVP was cancelled.')
    return redirect('event_detail', pk=pk)


@login_required
def event_attendance(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not event.user_can_manage(request.user):
        messages.error(request, 'You do not manage this event.')
        return redirect('event_detail', pk=pk)
    attendees = event.rsvps.filter(status=EventRSVP.Status.GOING).select_related('user')
    if request.method == 'POST':
        user_ids = request.POST.getlist('attended')
        for user_id in user_ids:
            Attendance.objects.get_or_create(event=event, user_id=user_id, defaults={'checked_in_by': request.user})
        Attendance.objects.filter(event=event).exclude(user_id__in=user_ids).delete()
        messages.success(request, 'Attendance saved.')
        return redirect('event_detail', pk=pk)
    checked = set(event.attendance_records.values_list('user_id', flat=True))
    return render(request, 'clubs/attendance.html', {'event': event, 'attendees': attendees, 'checked': checked})

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import MembershipRequest, AdminProfile


@login_required
def club_request_join(request, pk):
    club = get_object_or_404(Club, pk=pk)
    if request.method == 'POST':
        if ClubMembership.objects.filter(club=club, user=request.user).exists():
            messages.info(request, 'You are already a member.')
        else:
            MembershipRequest.objects.get_or_create(club=club, user=request.user)
            messages.success(request, f'Your request to join {club.name} has been sent!')
    return redirect('club_detail', pk=pk)


@login_required
@require_POST
def admin_pin_check(request):
    try:
        data = json.loads(request.body)
        pin  = data.get('pin', '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Bad request'}, status=400)
    try:
        profile = request.user.admin_profile
        ok = profile.check_pin(pin)
    except AdminProfile.DoesNotExist:
        ok = request.user.is_superuser and pin == 'admin'
    if ok:
        request.session['admin_pin_verified'] = True
    return JsonResponse({'ok': ok})


def admin_pin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or request.session.get('admin_pin_verified'):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Admin PIN required.')
        return redirect('dashboard')
    return wrapper


@login_required
@admin_pin_required
def admin_requests(request):
    pending = MembershipRequest.objects.filter(
        status=MembershipRequest.Status.PENDING
    ).select_related('user', 'club').order_by('-created_at')
    return render(request, 'clubs/admin_requests.html', {'pending': pending})


@login_required
@admin_pin_required
def admin_request_action(request, pk):
    req = get_object_or_404(MembershipRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            req.status = MembershipRequest.Status.APPROVED
            req.save()
            ClubMembership.objects.get_or_create(club=req.club, user=req.user)
            messages.success(request, f'{req.user} approved for {req.club}.')
        elif action == 'deny':
            req.status = MembershipRequest.Status.DENIED
            req.save()
            messages.info(request, f'{req.user} denied for {req.club}.')
    return redirect('admin_requests')


@login_required
def event_calendar(request):
    import calendar as cal_mod
    from datetime import date
    today = date.today()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))
    cal   = cal_mod.Calendar(firstweekday=6)
    weeks = cal.monthdatescalendar(year, month)
    events = Event.objects.filter(
        event_date__year=year,
        event_date__month=month,
    ).select_related('category').prefetch_related('clubs')
    events_by_date = {}
    for ev in events:
        d = ev.event_date.date()
        events_by_date.setdefault(d, []).append(ev)
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    context = {
        'weeks': weeks, 'events_by_date': events_by_date,
        'today': today, 'year': year, 'month': month,
        'month_name': cal_mod.month_name[month],
        'prev_year': prev_year, 'prev_month': prev_month,
        'next_year': next_year, 'next_month': next_month,
    }
    return render(request, 'clubs/calendar.html', context)