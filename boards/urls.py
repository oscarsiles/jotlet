from django.urls import path

from . import views

app_name = "boards"
urlpatterns = [
    path("", views.index.IndexView.as_view(), name="index"),
    path("all/", views.index.IndexAllBoardsView.as_view(), name="index-all"),
    path("create/", views.board.CreateBoardView.as_view(), name="board-create"),
    path("image_select/<str:image_type>/", views.board.ImageSelectView.as_view(), name="image-select"),
    path("list/<str:board_list_type>/", views.index.BoardListView.as_view(), name="board-list"),
    path("<slug:slug>/", views.board.BoardView.as_view(), name="board"),
    path("<slug:slug>/update/", views.board.UpdateBoardView.as_view(), name="board-update"),
    path("<slug:slug>/delete/", views.board.DeleteBoardView.as_view(), name="board-delete"),
    path("<slug:slug>/image/post/upload/", views.post.PostImageUploadView.as_view(), name="post-image-upload"),
    path("<slug:slug>/posts/approve/", views.post.ApprovePostsView.as_view(), name="board-posts-approve"),
    path("<slug:slug>/posts/delete/", views.post.DeletePostsView.as_view(), name="board-posts-delete"),
    path("<slug:slug>/qr/", views.board.QrView.as_view(), name="board-qr"),
    path("<slug:slug>/exports/", views.export.ExportView.as_view(), name="board-export"),
    path("<slug:slug>/exports/create/", views.export.ExportCreateView.as_view(), name="board-export-create"),
    path("<slug:slug>/exports/table/", views.export.ExportTablePartialView.as_view(), name="board-export-table"),
    path("<slug:slug>/exports/delete/", views.export.ExportDeleteView.as_view(), name="board-export-delete-all"),
    path(
        "<slug:slug>/exports/<uuid:pk>/delete/",
        views.export.ExportDeleteView.as_view(),
        name="board-export-delete",
    ),
    path(
        "<slug:slug>/exports/<uuid:pk>/download/",
        views.export.ExportDownloadView.as_view(),
        name="board-export-download",
    ),
    path("<slug:slug>/preferences/", views.board.BoardPreferencesView.as_view(), name="board-preferences"),
    path("<slug:slug>/topics/create/", views.topic.CreateTopicView.as_view(), name="topic-create"),
    path("<slug:slug>/topics/<uuid:pk>/update/", views.topic.UpdateTopicView.as_view(), name="topic-update"),
    path("<slug:slug>/topics/<uuid:pk>/delete/", views.topic.DeleteTopicView.as_view(), name="topic-delete"),
    path("<slug:slug>/topics/<uuid:pk>/fetch/", views.topic.TopicFetchView.as_view(), name="topic-fetch"),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/approve/",
        views.post.ApprovePostsView.as_view(),
        name="topic-posts-approve",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/delete/",
        views.post.DeletePostsView.as_view(),
        name="topic-posts-delete",
    ),
    path("<slug:slug>/topics/<uuid:topic_pk>/posts/create/", views.post.CreatePostView.as_view(), name="post-create"),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:pk>/update/",
        views.post.UpdatePostView.as_view(),
        name="post-update",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:pk>/delete/",
        views.post.DeletePostView.as_view(),
        name="post-delete",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:pk>/fetch/post/",
        views.post.PostFetchView.as_view(),
        name="post-fetch",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:pk>/fetch/footer/",
        views.post.PostFooterFetchView.as_view(),
        name="post-footer-fetch",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:pk>/approval/",
        views.post.PostToggleApprovalView.as_view(),
        name="post-toggle-approval",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:post_pk>/reply/",
        views.post.CreatePostView.as_view(),
        name="post-reply",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:pk>/reaction/",
        views.reaction.PostReactionView.as_view(),
        name="post-reaction",
    ),
    path(
        "<slug:slug>/topics/<uuid:topic_pk>/posts/<uuid:pk>/reactions/delete/",
        views.reaction.ReactionsDeleteView.as_view(),
        name="post-reactions-delete",
    ),
]
