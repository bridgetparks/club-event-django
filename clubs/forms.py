from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Club, ClubMembership, Event, EventCategory, EventRSVP, EventTag, validate_gonzaga_email

class GonzagaSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(validators=[validate_gonzaga_email])

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        validate_gonzaga_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account already exists for this email.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].lower().strip()
        user.email = self.cleaned_data['email'].lower().strip()
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        if commit:
            user.save()
        return user

class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}

class MembershipForm(forms.ModelForm):
    class Meta:
        model = ClubMembership
        fields = ['user', 'club']

class EventForm(forms.ModelForm):
    tag_names = forms.CharField(required=False, help_text='Comma-separated tags, e.g. service, food, freshman-friendly')

    class Meta:
        model = Event
        fields = ['title', 'description', 'event_date', 'location', 'clubs', 'category', 'tag_names', 'cover_image', 'capacity']
        widgets = {
            'event_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'clubs': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, manageable_clubs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if manageable_clubs is not None:
            self.fields['clubs'].queryset = manageable_clubs
        if self.instance.pk:
            self.fields['tag_names'].initial = ', '.join(self.instance.tags.values_list('name', flat=True))

    def save_tags(self, event):
        names = [n.strip() for n in self.cleaned_data.get('tag_names', '').split(',') if n.strip()]
        tags = [EventTag.objects.get_or_create(name=name)[0] for name in names]
        event.tags.set(tags)

    def save(self, commit=True):
        event = super().save(commit=commit)
        if commit:
            self.save_m2m()
            self.save_tags(event)
        return event
