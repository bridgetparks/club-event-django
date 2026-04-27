from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


def validate_gonzaga_email(value: str):
    domains = getattr(settings, 'GONZAGA_EMAIL_DOMAINS', ['gonzaga.edu', 'zagmail.gonzaga.edu'])
    domain = value.split('@')[-1].lower() if '@' in value else ''
    if domain not in domains:
        raise ValidationError('Use your Gonzaga email address to sign up.')


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email or self.user.username


class Club(models.Model):
    name = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, through='ClubMembership', related_name='clubs')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def user_is_leader(self, user):
        return user.is_authenticated and (user.is_superuser or self.leaders.filter(user=user).exists())


class ClubLeadership(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='leaders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_leaderships')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('club', 'user')
        ordering = ['club__name', 'user__last_name']

    def __str__(self):
        return f'{self.user} leads {self.club}'


class ClubMembership(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('club', 'user')
        ordering = ['club__name', 'user__last_name', 'user__first_name']

    def __str__(self):
        return f'{self.user} in {self.club}'


class EventCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    color = models.CharField(max_length=24, default='#0d6efd')

    class Meta:
        verbose_name_plural = 'event categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class EventTag(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    event_date = models.DateTimeField()
    location = models.CharField(max_length=220, blank=True)
    clubs = models.ManyToManyField(Club, related_name='events')
    category = models.ForeignKey(EventCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    tags = models.ManyToManyField(EventTag, blank=True, related_name='events')
    cover_image = models.ImageField(upload_to='event_covers/', blank=True, null=True)
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text='Leave blank for unlimited capacity.')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date', 'title']

    def __str__(self):
        return self.title

    @property
    def is_past(self):
        return self.event_date < timezone.now()

    @property
    def going_count(self):
        return self.rsvps.filter(status=EventRSVP.Status.GOING).count()

    @property
    def waitlist_count(self):
        return self.rsvps.filter(status=EventRSVP.Status.WAITLISTED).count()

    @property
    def spots_left(self):
        if self.capacity is None:
            return None
        return max(self.capacity - self.going_count, 0)

    def user_can_manage(self, user):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return self.clubs.filter(leaders__user=user).exists()

    def rsvp_user(self, user):
        if not user.is_authenticated:
            raise ValidationError('Login required.')
        if self.is_past:
            raise ValidationError('This event has already happened.')
        status = EventRSVP.Status.GOING
        if self.capacity is not None and self.going_count >= self.capacity:
            status = EventRSVP.Status.WAITLISTED
        rsvp, created = EventRSVP.objects.get_or_create(event=self, user=user, defaults={'status': status})
        if not created and rsvp.status == EventRSVP.Status.CANCELLED:
            rsvp.status = status
            rsvp.save(update_fields=['status', 'updated_at'])
        return rsvp

    def promote_waitlist(self):
        if self.capacity is None:
            return
        while self.going_count < self.capacity:
            next_rsvp = self.rsvps.filter(status=EventRSVP.Status.WAITLISTED).order_by('created_at').first()
            if not next_rsvp:
                break
            next_rsvp.status = EventRSVP.Status.GOING
            next_rsvp.save(update_fields=['status', 'updated_at'])


class EventRSVP(models.Model):
    class Status(models.TextChoices):
        GOING = 'going', 'Going'
        WAITLISTED = 'waitlisted', 'Waitlisted'
        CANCELLED = 'cancelled', 'Cancelled'

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_rsvps')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.GOING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['event__event_date', 'created_at']

    def __str__(self):
        return f'{self.user} {self.status} for {self.event}'


class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendance_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_checked')
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-checked_in_at']

    def __str__(self):
        return f'{self.user} attended {self.event}'
