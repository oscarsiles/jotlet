from django.urls import path

from . import views

app_name = 'catalog'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('<int:pk>/', views.BoardView.as_view(), name='board'),
]