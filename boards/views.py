from django.shortcuts import render
from django.views import generic

from .models import Board, Topic, Post

# Create your views here.
class IndexView(generic.TemplateView):
    template_name = 'boards/index.html'

class BoardView(generic.DetailView):
    model = Board
    template_name = 'boards/board.html'
