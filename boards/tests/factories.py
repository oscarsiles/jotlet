import json

import factory
from faker import Faker

from accounts.tests.factories import UserFactory
from boards.models import AdditionalData, BgImage, Board, BoardPreferences, Image, Post, PostImage, Reaction, Topic
from jotlet.tests.factories import JSONFactory

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
    session_key = factory.Sequence(lambda n: fake.unique.sha1())


class AdditionalDataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AdditionalData

    post = factory.SubFactory(PostFactory)


class JSONDataFactory(AdditionalDataFactory):
    json = factory.SubFactory(JSONFactory)


class MiscDataFactory(JSONDataFactory):
    data_type = "m"


class ChemdoodleDataFactory(JSONDataFactory):
    data_type = "c"
    json = json.loads(
        '{"m":[{"a":[{"x":206.99402945382255,"y":131.39880044119698,"i":"a3"},{"x":226.99402945382255,'
        '"y":131.39880044119698,"i":"a79"},{"x":236.99402945382258,"y":148.71930851688575,"i":"a80"},'
        '{"x":226.9940294538226,"y":166.03981659257454,"i":"a81"},'
        '{"x":206.9940294538226,"y":166.0398165925746,"i":"a82"},'
        '{"x":196.99402945382255,"y":148.71930851688586,"i":"a83"}],"i":"m3",'
        '"b":[{"b":0,"e":1,"i":"b84"},{"b":1,"e":2,"i":"b85","o":2},{"b":2,"e":3,"i":"b86"},'
        '{"b":3,"e":4,"i":"b87","o":2},{"b":4,"e":5,"i":"b88"},{"b":5,"e":0,"i":"b89","o":2}]}]}'
    )  # benzene ChemDoole JSON


# class FileDataFactory(AdditionalDataFactory):
#     data_type = "f"
#     file = factory.django.FileField(filename="the_file.dat")


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
