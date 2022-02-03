from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string

from shortuuidfield import ShortUUIDField

# Create your models here.
class Board(models.Model):
    title = models.CharField(max_length=50)
    uuid = ShortUUIDField(unique=True)
    slug = models.SlugField(max_length=6, unique=True, null=True)
    description = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="boards")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        slug_save(self)
        super(Board, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.slug})

    class Meta:
        permissions = (
            ('can_view_all_boards', "Can view all boards"),
            )
    

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
        return reverse("boards:board", kwargs={"slug": self.board.slug})
    

class Post(models.Model):
    content = models.TextField(max_length=400)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name='posts')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.content

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"pk": self.topic.board.slug})


def slug_save(obj):
    """ A function to generate a 6 character numeric slug and see if it has been used."""
    if not obj.slug: # if there isn't a slug
        obj.slug = get_random_string(6, '0123456789') # create one
        slug_is_wrong = True  
        while slug_is_wrong: # keep checking until we have a valid slug
            slug_is_wrong = False
            other_objs_with_slug = type(obj).objects.filter(slug=obj.slug)
            if len(other_objs_with_slug) > 0:
                # if any other objects have current slug
                slug_is_wrong = True
            if slug_is_wrong:
                # create another slug and check it again
                obj.slug = get_random_string(6)
