from django.contrib import admin


from .models import Board, Post, Topic

# Register your models here.
# admin.site.register(Board)
# admin.site.register(Topic)
# admin.site.register(Post)

class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1

class PostInline(admin.TabularInline):
    model = Post
    extra = 1
@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'uuid', 'created_at', 'updated_at',)
    fields = ('title', 'description',)
    inlines =[TopicInline]

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('subject', 'board', 'created_at', 'updated_at')
    fields = ('subject', 'board',)
    inlines = [PostInline]

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('content', 'topic', 'created_at', 'updated_at')
    fields = ('content', 'topic',)