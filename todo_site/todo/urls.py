
from django.urls import path
from . import views

urlpatterns = [
    path('', views.todo_list, name='todo_list'),
    path('add/', views.add_todo, name='add_todo'),
    path('edit/<int:pk>/', views.edit_todo, name='edit_todo'),
    path('delete/<int:pk>/', views.delete_todo, name='delete_todo'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms_of_services/', views.terms_of_services, name='terms_of_services'),
    # path('settings/', views.settings, name='settings'),
]