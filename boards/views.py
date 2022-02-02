from ast import arg
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.template import RequestContext
from django.urls import reverse_lazy
from django.views import generic

from .models import Board, Topic, Post

# Create your views here.
class IndexView(generic.TemplateView):
    template_name = 'boards/index.html'
    
    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['boards'] = Board.objects.all()
        return context

class BoardView(generic.DetailView):
    model = Board
    template_name = 'boards/board.html'

class CreateBoardView(LoginRequiredMixin, generic.CreateView):
    model = Board
    fields = ['title', 'description']
    template_name = 'boards/board_form.html'

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

class CreateTopicView(LoginRequiredMixin, generic.CreateView):
    model = Topic
    fields = ['subject']
    template_name = 'boards/topic_form.html'

    def form_valid(self, form):
        form.instance.board_id = self.kwargs.get('board_pk')
        return super(CreateTopicView, self).form_valid(form)

class UpdateTopicView(LoginRequiredMixin, generic.UpdateView):
    model = Topic
    fields = ['subject']
    template_name = 'boards/topic_form.html'

class DeleteTopicView(LoginRequiredMixin, generic.DeleteView):
    model = Topic
    template_name = 'boards/topic_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('boards:board', kwargs={'pk': self.object.board_id})

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

class UpdatePostView(generic.UpdateView):
    model = Post
    fields = ['content']
    template_name = 'boards/post_form.html'

class DeletePostView(generic.DeleteView):
    model = Post
    template_name = 'boards/post_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('boards:board', kwargs={'pk': self.object.topic.board_id})
