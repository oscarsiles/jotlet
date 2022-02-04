from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import generic

from .models import Board, Topic, Post
from .forms import SearchBoardsForm

def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)

class IndexView(generic.FormView):
    model = Board
    template_name = 'boards/index.html'

    form_class = SearchBoardsForm

    def form_valid(self, form):
        self.form = form
        try:
            Board.objects.get(slug=self.form.cleaned_data['board_slug'])
            return HttpResponseRedirect(self.get_success_url())
        except:
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['boards'] = Board.objects.all()
        return context
    
    def get_success_url(self):
        return reverse('boards:board', kwargs={'slug': self.form.cleaned_data['board_slug']})

class BoardView(generic.DetailView):
    model = Board
    template_name = 'boards/board.html'

class CreateBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Board
    fields = ['title', 'description']
    template_name = 'boards/board_form.html'

    def test_func(self):
        return self.request.user.has_perm('boards.add_board')

    def form_valid(self, form):
        board = form.save(commit=False)
        board.owner = self.request.user
        board.save()
        return super(CreateBoardView, self).form_valid(form)

class UpdateBoardView(LoginRequiredMixin, generic.UpdateView):
    model = Board
    fields = ['title', 'description']
    template_name = 'boards/board_form.html'

class DeleteBoardView(LoginRequiredMixin, generic.DeleteView):
    model = Board
    template_name = 'boards/board_confirm_delete.html'
    success_url = '/'

class CreateTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Topic
    fields = ['subject']
    template_name = 'boards/topic_form.html'
    
    def test_func(self):
        board = Board.objects.get_queryset().get(slug=self.kwargs['slug'])
        return self.request.user == board.owner or self.request.user.is_staff

    def form_valid(self, form):
        form.instance.board_id = Board.objects.get_queryset().get(slug=self.kwargs['slug']).id
        return super(CreateTopicView, self).form_valid(form)

    def get_success_url(self) -> str:
        channel_group_send(f"board_{self.kwargs.get('slug')}", {
            'type': "topic_created",
            'topic_pk': self.object.pk,
            'topic_subject': self.object.subject,
            },
        )
        return super().get_success_url()

class UpdateTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Topic
    fields = ['subject']
    template_name = 'boards/topic_form.html'

    def test_func(self):
        board = Board.objects.get_queryset().get(slug=self.kwargs['slug'])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_success_url(self) -> str:
        channel_group_send(f"board_{self.kwargs.get('slug')}", {
            'type': "topic_updated",
            'topic_pk': self.object.pk,
            'topic_subject': self.object.subject,
            },
        )
        return super().get_success_url()

class DeleteTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Topic
    template_name = 'boards/topic_confirm_delete.html'

    def test_func(self):
        board = Board.objects.get_queryset().get(slug=self.kwargs['slug'])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_success_url(self):
        channel_group_send(f"board_{self.kwargs.get('slug')}", {
            'type': "topic_deleted",
            'topic_pk': self.object.pk,
            },
        )
        return reverse_lazy('boards:board', kwargs={'slug': self.kwargs['slug']})

class CreatePostView(generic.CreateView):
    model = Post
    fields = ['content']
    template_name = 'boards/post_form.html'

    def form_valid(self, form):
        form.instance.topic_id = self.kwargs.get('topic_pk')
        if not self.request.session.session_key: # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        form.instance.session_key = self.request.session.session_key
        return super(CreatePostView, self).form_valid(form)

    def get_success_url(self):
        channel_group_send(f"board_{self.kwargs.get('slug')}", {
            'type': "post_created",
            'topic_pk': self.kwargs.get('topic_pk'),
            'post_pk': self.object.pk,
            'post_content': self.object.content,
            'post_session_key': self.request.session.session_key,
            })
        return reverse_lazy('boards:board', kwargs={'slug': self.kwargs['slug'],})


class UpdatePostView(UserPassesTestMixin, generic.UpdateView):
    model = Post
    fields = ['content']
    template_name = 'boards/post_form.html'

    def test_func(self):
        post = Post.objects.get_queryset().get(pk=self.kwargs['pk'])
        return self.request.session.session_key == post.session_key or self.request.user.has_perm('boards.change_post') or self.request.user.is_staff

    def get_success_url(self):
        channel_group_send(f"board_{self.kwargs.get('slug')}", {
            'type': "post_updated",
            'post_pk': self.object.pk,
            'post_content': self.object.content,
            },
        )
        return reverse_lazy('boards:board', kwargs={'slug': self.kwargs['slug'],})


class DeletePostView(UserPassesTestMixin, generic.DeleteView):
    model = Post
    template_name = 'boards/post_confirm_delete.html'

    def test_func(self):
        post = Post.objects.get_queryset().get(pk=self.kwargs['pk'])
        return self.request.session.session_key == post.session_key or self.request.user.has_perm('boards.delete_post') or self.request.user.is_staff

    def get_success_url(self):
        channel_group_send(f"board_{self.kwargs.get('slug')}", {
            'type': "post_deleted",
            'post_pk': self.object.pk,
            },
        )
        return reverse_lazy('boards:board', kwargs={'slug': self.kwargs['slug'],})
