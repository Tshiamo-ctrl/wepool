# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('referral-matrix/', views.referral_matrix_view, name='referral_matrix'),
    path('api/referral-data/', views.get_referral_data, name='get_referral_data'),
    path('direct-referrals/', views.direct_referrals_view, name='direct_referrals'),
]
