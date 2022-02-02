from django.db import models
from django.urls import reverse

from shortuuidfield import ShortUUIDField

# Create your models here.
class Board(models.Model):
    title = models.CharField(max_length=50)
    uuid = ShortUUIDField(unique=True)
    description = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"pk": self.pk})
    

class Topic(models.Model):
    subject = models.CharField(max_length=50)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, null=True, related_name='topics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.subject

    def get_board_name(self):
        return self.board.title

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"pk": self.board_id})
    

class Post(models.Model):
    content = models.TextField(max_length=400)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name='posts')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.content

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"pk": self.topic.board_id})
