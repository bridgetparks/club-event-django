from django.contrib import admin
from .models import (
    AdminProfile, Club, ClubLeadership, ClubMembership,
    MembershipRequest, Event, EventCategory, EventTag,
    EventRSVP, Attendance, Profile,
)

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display  = ['name', 'member_count', 'created_at']
    search_fields = ['name']

    def member_count(self, obj):
        return obj.memberships.count()

@admin.register(MembershipRequest)
class MembershipRequestAdmin(admin.ModelAdmin):
    list_display  = ['user', 'club', 'status', 'created_at']
    list_filter   = ['status', 'club']
    list_editable = ['status']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display  = ['title', 'event_date', 'location', 'going_count']
    search_fields = ['title', 'location']
    list_filter   = ['category', 'event_date']

    def going_count(self, obj):
        return obj.going_count

admin.site.register(AdminProfile)
admin.site.register(ClubLeadership)
admin.site.register(ClubMembership)
admin.site.register(EventCategory)
admin.site.register(EventTag)
admin.site.register(EventRSVP)
admin.site.register(Attendance)
admin.site.register(Profile)
