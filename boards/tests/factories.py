import factory
from faker import Faker

from accounts.tests.factories import UserFactory
from boards.models import BgImage, Board, BoardPreferences, Image, Post, PostImage, Reaction, Topic

fake = Faker()


class BoardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Board

    owner = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Test Board {n}")
    description = factory.Sequence(lambda n: f"Test Board Description {n}")


class BoardPreferencesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BoardPreferences

    board = factory.SubFactory(BoardFactory)


class TopicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Topic

    board = factory.SubFactory(BoardFactory)
    subject = factory.Sequence(lambda n: f"Test Topic {n}")


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    user = None
    topic = factory.SubFactory(TopicFactory)
    content = factory.Sequence(lambda n: f"Test Post {n}")


class ReactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reaction

    post = factory.SubFactory(PostFactory)
    session_key = factory.LazyFunction(lambda: fake.unique.sha1())


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    title = factory.Sequence(lambda n: f"Test Image {n}")
    image = factory.django.ImageField(filename="example.png", format="png", width=100, height=100)


class BgImageFactory(ImageFactory):
    class Meta:
        model = BgImage


class PostImageFactory(ImageFactory):
    class Meta:
        model = PostImage

    board = factory.SubFactory(BoardFactory)
