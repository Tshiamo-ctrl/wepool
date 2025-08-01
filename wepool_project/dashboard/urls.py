# dashboard/urls.py - Add the missing override_history URL
from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.view_all_users, name='view_all_users'),
    path('users/<int:profile_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:profile_id>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:profile_id>/quick-override/', views.quick_override, name='quick_override'),
    path('users/<int:profile_id>/remove-override/', views.remove_override, name='remove_override'),
    path('paying-queue/', views.paying_queue, name='paying_queue'),
    path('sponsored-queue/', views.sponsored_queue, name='sponsored_queue'),
    path('yellow-members/', views.yellow_members, name='yellow_members'),
    path('qualified-sponsored/', views.qualified_sponsored, name='qualified_sponsored'),
    path('assign/', views.assign_members, name='assign_members'),
    path('export/', views.export_data, name='export_data'),
    path('override-history/', views.override_history, name='override_history'),  # Add this line

    # API and utility endpoints
    path('api/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('bulk-update-status/', views.bulk_update_status, name='bulk_update_status'),
    path('process-yellow/', views.process_yellow_queue, name='process_yellow_queue'),
]
