import factory
from faker import Faker

from accounts.tests.factories import UserFactory
from boards.models import BgImage, Board, Image, Post, PostImage, Reaction, Topic

fake = Faker()


class BoardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Board

    owner = factory.SubFactory(UserFactory)
    title = factory.Faker("text", max_nb_chars=50)
    description = factory.Faker("text", max_nb_chars=100)


class TopicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Topic

    board = factory.SubFactory(BoardFactory)
    subject = factory.Faker("text", max_nb_chars=400)


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    topic = factory.SubFactory(TopicFactory)
    content = factory.Faker("text", max_nb_chars=1000)


class ReactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reaction

    post = factory.SubFactory(PostFactory)
    session_key = factory.LazyFunction(lambda: fake.unique.sha1())


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    title = factory.Faker("text", max_nb_chars=50)
    image = factory.django.ImageField()


class BgImageFactory(ImageFactory):
    class Meta:
        model = BgImage


class PostImageFactory(ImageFactory):
    class Meta:
        model = PostImage

    board = factory.SubFactory(BoardFactory)
