import factory
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

from accounts.models import UserProfile

USER_TEST_PASSWORD = "test_password"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.LazyFunction(lambda: make_password(USER_TEST_PASSWORD))


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
