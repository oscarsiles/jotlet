import factory
from faker import Faker

from accounts.tests.factories import UserFactory
from boards.models import Board, Image, Post, Reaction, Topic

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


# black_pixel_gif = (
#     b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00"
#     b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
# )


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    title = factory.Faker("text", max_nb_chars=50)
    image = factory.django.ImageField()


class BgImageFactory(ImageFactory):
    type = "b"


class PostImageFactory(ImageFactory):
    type = "p"
    board = factory.SubFactory(BoardFactory)
