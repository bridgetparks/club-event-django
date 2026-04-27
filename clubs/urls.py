from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('clubs/', views.club_list, name='club_list'),
    path('clubs/new/', views.club_create, name='club_create'),
    path('clubs/<int:pk>/', views.club_detail, name='club_detail'),
    path('clubs/<int:pk>/edit/', views.club_update, name='club_update'),
    path('clubs/<int:pk>/delete/', views.club_delete, name='club_delete'),
    path('memberships/', views.membership_list, name='membership_list'),
    path('memberships/add/', views.membership_add, name='membership_add'),
    path('memberships/<int:pk>/remove/', views.membership_remove, name='membership_remove'),
    path('events/', views.event_list, name='event_list'),
    path('events/new/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_update, name='event_update'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:pk>/rsvp/', views.event_rsvp, name='event_rsvp'),
    path('events/<int:pk>/cancel-rsvp/', views.event_cancel_rsvp, name='event_cancel_rsvp'),
    path('events/<int:pk>/attendance/', views.event_attendance, name='event_attendance'),
]
