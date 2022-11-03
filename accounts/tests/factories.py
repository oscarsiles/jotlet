import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from accounts.models import UserProfile

USER_TEST_PASSWORD = "test_password"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.LazyFunction(lambda: make_password(USER_TEST_PASSWORD))
    optin_newsletter = False
    is_staff = False
    is_superuser = False


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
