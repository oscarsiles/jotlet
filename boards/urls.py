from django.urls import path

from . import views

app_name = "boards"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("all/", views.IndexAllBoardsView.as_view(), name="index-all"),
    path("create/", views.CreateBoardView.as_view(), name="board-create"),
    path("list/", views.BoardListView.as_view(), name="board-list"),
    path("image_select/<str:type>/", views.ImageSelectView.as_view(), name="image-select"),
    path("<slug:slug>/", views.BoardView.as_view(), name="board"),
    path("<slug:slug>/update/", views.UpdateBoardView.as_view(), name="board-update"),
    path("<slug:slug>/delete/", views.DeleteBoardView.as_view(), name="board-delete"),
    path("<slug:slug>/image/post/upload/", views.PostImageUploadView.as_view(), name="image-upload"),
    path("<slug:slug>/qr/", views.QrView.as_view(), name="board-qr"),
    path("<slug:slug>/preferences/", views.BoardPreferencesView.as_view(), name="board-preferences"),
    path("<slug:slug>/topics/create/", views.CreateTopicView.as_view(), name="topic-create"),
    path("<slug:slug>/topics/<int:pk>/update/", views.UpdateTopicView.as_view(), name="topic-update"),
    path("<slug:slug>/topics/<int:pk>/delete/", views.DeleteTopicView.as_view(), name="topic-delete"),
    path("<slug:slug>/topics/<int:pk>/fetch/", views.TopicFetchView.as_view(), name="topic-fetch"),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/delete/",
        views.DeleteTopicPostsView.as_view(),
        name="topic-posts-delete",
    ),
    path("<slug:slug>/topics/<int:topic_pk>/posts/create/", views.CreatePostView.as_view(), name="post-create"),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/update/", views.UpdatePostView.as_view(), name="post-update"
    ),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/delete/", views.DeletePostView.as_view(), name="post-delete"
    ),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/fetch/post/",
        views.PostFetchView.as_view(),
        name="post-fetch",
    ),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/fetch/footer/",
        views.PostFooterFetchView.as_view(),
        name="post-footer-fetch",
    ),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/approval/",
        views.PostToggleApprovalView.as_view(),
        name="post-toggle-approval",
    ),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:post_pk>/reply/",
        views.CreatePostView.as_view(),
        name="post-reply",
    ),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/reaction/",
        views.PostReactionView.as_view(),
        name="post-reaction",
    ),
    path(
        "<slug:slug>/topics/<int:topic_pk>/posts/<int:pk>/reactions/delete/",
        views.ReactionsDeleteView.as_view(),
        name="post-reactions-delete",
    ),
]
