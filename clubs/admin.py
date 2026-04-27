from django.contrib import admin
from .models import Attendance, Club, ClubLeadership, ClubMembership, Event, EventCategory, EventRSVP, EventTag, Profile

class ClubLeadershipInline(admin.TabularInline):
    model = ClubLeadership
    extra = 1

class ClubMembershipInline(admin.TabularInline):
    model = ClubMembership
    extra = 0

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count', 'created_at')
    search_fields = ('name', 'description')
    inlines = [ClubLeadershipInline, ClubMembershipInline]

    def member_count(self, obj):
        return obj.memberships.count()

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_date', 'location', 'capacity', 'going', 'waitlisted')
    list_filter = ('category', 'clubs', 'event_date')
    search_fields = ('title', 'description', 'location')
    filter_horizontal = ('clubs', 'tags')

    def going(self, obj): return obj.going_count
    def waitlisted(self, obj): return obj.waitlist_count

admin.site.register(Profile)
admin.site.register(ClubLeadership)
admin.site.register(ClubMembership)
admin.site.register(EventCategory)
admin.site.register(EventTag)
admin.site.register(EventRSVP)
admin.site.register(Attendance)
