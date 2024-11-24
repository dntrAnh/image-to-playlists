from django.urls import path
from core import views

urlpatterns = [
    path('', views.home, name='home'), 
    path('core_search/', views.core_search_data, name='core_search_data'),
    path('past_searches/', views.past_searches, name='past_searches'),
]
