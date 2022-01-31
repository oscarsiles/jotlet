from django.db import models

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

class Topic(models.Model):
    subject = models.CharField(max_length=50)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, null=True, related_name='topics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.subject

class Post(models.Model):
    content = models.TextField(max_length=400)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.content