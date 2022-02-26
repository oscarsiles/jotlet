from tkinter import W
from django.urls import reverse
from django.test import TestCase

from django.contrib.auth.models import User

from django_fakeredis import FakeRedis

from boards.models import Board, BoardPreferences, Topic, Post


class BoardModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    def test_title_max_length(self):
        board = Board.objects.get(id=1)
        max_length = board._meta.get_field("title").max_length
        self.assertEqual(max_length, 50)

    def test_description_max_length(self):
        board = Board.objects.get(id=1)
        max_length = board._meta.get_field("description").max_length
        self.assertEqual(max_length, 100)

    def test_object_name_is_title(self):
        board = Board.objects.get(id=1)
        self.assertEqual(str(board), board.title)

    def test_slug_format(self):
        slug = Board.objects.get(id=1).slug
        self.assertRegex(slug, r"^\d{6}$")

    def test_board_remain_after_user_delete(self):
        user = User.objects.get(username="testuser1")
        board_count_before = Board.objects.count()
        user.delete()
        board_count_after = Board.objects.count()
        self.assertEqual(board_count_before, board_count_after)

    def test_get_absolute_url(self):
        board = Board.objects.get(id=1)
        self.assertEqual(board.get_absolute_url(), f"/boards/{board.slug}/")


class BoardPreferencesModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    def test_board_has_preferences(self):
        board = Board.objects.get(id=1)
        self.assertIsNotNone(board.preferences)

    def test_preferences_name(self):
        preferences = BoardPreferences.objects.get(board=Board.objects.get(id=1))
        self.assertEqual(str(preferences), "Test Board preferences")

    def test_get_absolute_url(self):
        preferences = BoardPreferences.objects.get(board=Board.objects.get(id=1))
        self.assertEqual(preferences.get_absolute_url(), f"/boards/{preferences.board.slug}/preferences/")

    def test_preferences_deleted_after_board_delete(self):
        board = Board.objects.get(id=1)
        preferences = BoardPreferences.objects.get(board=board)
        board.delete()
        self.assertRaises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, id=preferences.id)


class TopicModelTest(TestCase):
    @classmethod
    @FakeRedis("django.core.cache.cache")
    def setUpTestData(cls):
        # Create two users
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)
        Topic.objects.create(subject="Test Topic", board=Board.objects.get(title="Test Board"))
        Board.objects.create(title="Test Board 2", description="Test Board 2 Description", owner=test_user2)
        Topic.objects.create(subject="Test Topic 2", board=Board.objects.get(title="Test Board 2"))

    def test_subject_max_length(self):
        topic = Topic.objects.get(id=1)
        max_length = topic._meta.get_field("subject").max_length
        self.assertEqual(max_length, 50)

    def test_object_name_is_subject(self):
        topic = Topic.objects.get(id=1)
        self.assertEqual(str(topic), topic.subject)

    def test_get_board_name(self):
        topic = Topic.objects.get(id=1)
        self.assertEqual(topic.get_board_name(), topic.board.title)

    def test_get_absolute_url(self):
        topic = Topic.objects.get(id=1)
        self.assertEqual(topic.get_absolute_url(), f"/boards/{topic.board.slug}/")

    # permissions
    @FakeRedis("django.core.cache.cache")
    def test_anonymous_user_permissions(self):
        board = Board.objects.get(id=1)
        topic = Topic.objects.get(board=board)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("boards:topic-fetch", kwargs={"slug": board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(id=1)
        topic = Topic.objects.get(board=board)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(str(response.context["user"]), "testuser2")
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        topic = Topic.objects.get(board=board)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(str(response.context["user"]), "testuser1")
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)

    def test_topic_deleted_after_board_delete(self):
        board = Board.objects.get(id=1)
        topic = Topic.objects.get(board=board)
        board.delete()
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, id=topic.id)
