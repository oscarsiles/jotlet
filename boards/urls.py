from django.urls import path

from . import views

app_name = 'boards'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('create/', views.CreateBoardView.as_view(), name='board-create'),
    path('<slug:slug>/', views.BoardView.as_view(), name='board'),
    path('<slug:slug>/update/', views.UpdateBoardView.as_view(), name='board-update'),
    path('<slug:slug>/delete/', views.DeleteBoardView.as_view(), name='board-delete'),
    path('<slug:slug>/topics/create/', views.CreateTopicView.as_view(), name='topic-create'),
    path('<slug:slug>/topics/<int:pk>/update/', views.UpdateTopicView.as_view(), name='topic-update'),
    path('<slug:slug>/topics/<int:pk>/delete/', views.DeleteTopicView.as_view(), name='topic-delete'),
    path('<slug:slug>/topics/<int:topic_pk>/posts/create/', views.CreatePostView.as_view(), name='post-create'),
    path('<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/update/', views.UpdatePostView.as_view(), name='post-update'),
    path('<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/delete/', views.DeletePostView.as_view(), name='post-delete'),
]
