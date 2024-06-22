from django.urls import path

from . import views

app_name = 'core'
urlpatterns = [
    path('', views.index, name='index'),
    path('address/', views.address, name='address')
]
