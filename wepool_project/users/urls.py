# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.user_dashboard, name='user_dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(http_method_names=['get', 'post']), name='logout'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('profile/update/', views.update_profile, name='update_profile'),

    # AJAX endpoints
    path('api/update-techconnect/', views.update_techconnect_status, name='update_techconnect'),
    path('api/referral-tree/', views.referral_tree_data, name='referral_tree_data'),
    path('api/check-referrer/', views.check_referrer_exists, name='check_referrer'),
    path('api/debug-login/', views.debug_login, name='debug_login'),  # For debugging login issues

    # Password reset
    path('password-reset/',
         auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
         name='password_reset_complete'),
]
