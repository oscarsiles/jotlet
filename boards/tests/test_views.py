import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from django.contrib.auth.models import Permission, User

from django_fakeredis import FakeRedis

from boards.models import Board, Image, Topic, Post, BACKGROUND_TYPE, IMAGE_TYPE


class IndexViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)

    def test_board_search_success(self):
        board = Board.objects.get(id=1)
        response = self.client.post(reverse("boards:index"), {"board_slug": board.slug})
        self.assertEqual(response.status_code, 302)

    def test_board_search_invalid(self):
        response = self.client.post(reverse("boards:index"), {"board_slug": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "ID format needs to be ######.")

    def test_board_search_not_found(self):
        board = Board.objects.get(id=1)
        bad_slug = "000000" if board.slug != "000000" else "111111"
        response = self.client.post(reverse("boards:index"), {"board_slug": bad_slug})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "Board does not exist.")

    def test_board_search_no_slug(self):
        response = self.client.post(reverse("boards:index"), {})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "This field is required.")

    def test_board_non_staff_all_boards(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get("all_boards"))

    def test_board_staff_all_boards(self):
        test_user2 = User.objects.create_user(username="testuser2", password="1X<ISRUkw+tuK", is_staff=True)
        for i in range(10):
            Board.objects.create(title=f"Test Board {i}", description=f"Test Board Description {i}", owner=test_user2)
        login = self.client.login(username="testuser2", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get("all_boards"))
        self.assertEqual(len(response.context.get("all_boards")), 11)


class BoardViewTest(TestCase):
    @classmethod
    @FakeRedis("django.core.cache.cache")
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)


class BoardPreferencesViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_board_preferences_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/boards/{board.slug}/preferences/")

    def test_board_references_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_board_preferences_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)


class CreateBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(response.status_code, 302)

    def test_user_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(str(response.context["user"]), "testuser1")
        self.assertEqual(response.status_code, 200)

    def test_board_create_success(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("boards:board-create"), {"title": "Test Board", "description": "Test Board Description"}
        )
        self.assertEqual(response.status_code, 302)
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.description, "Test Board Description")

    def test_board_create_blank(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("boards:board-create"), {"title": "", "description": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "This field is required.")
        self.assertFormError(response, "form", "description", "This field is required.")

    def test_board_create_invalid(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("boards:board-create"), {"title": "x" * 51, "description": "x" * 101})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "Ensure this value has at most 50 characters (it has 51).")
        self.assertFormError(
            response, "form", "description", "Ensure this value has at most 100 characters (it has 101)."
        )


class UpdateBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        login = self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_update_success(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "Test Board NEW", "description": "Test Board Description NEW"},
        )
        self.assertEqual(response.status_code, 302)
        board = Board.objects.get(id=1)
        self.assertEqual(board.title, "Test Board NEW")
        self.assertEqual(board.description, "Test Board Description NEW")

    def test_board_update_blank(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "", "description": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "This field is required.")
        self.assertFormError(response, "form", "description", "This field is required.")

    def test_board_update_invalid(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "x" * 51, "description": "x" * 101},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "Ensure this value has at most 50 characters (it has 51).")
        self.assertFormError(
            response, "form", "description", "Ensure this value has at most 100 characters (it has 101)."
        )


class DeleteBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)

    def test_staff_permissions(self):
        staff_user = User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        login = self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)


class TopicCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        login = self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_topic_create_success(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": "Test Topic"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic"))

    def test_topic_create_blank(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "subject", "This field is required.")

    def test_topic_create_invalid(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": "x" * 100},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "subject", "Ensure this value has at most 50 characters (it has 100).")


class TopicUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        login = self.client.login(username="staff", password="83jKJ+!fdjP")
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)

    def test_topic_update_success(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(id=1)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}),
            data={"subject": "Test Topic NEW"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic NEW"))

    def test_topic_update_blank(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(id=1)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "subject", "This field is required.")

    def test_topic_update_invalid(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(id=1)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}),
            data={"subject": "x" * 100},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "subject", "Ensure this value has at most 50 characters (it has 100).")


class TopicDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, id=topic.id)

    def test_staff_permissions(self):
        staff_user = User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        login = self.client.login(username="staff", password="83jKJ+!fdjP")
        topic = Topic.objects.get(id=1)
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, id=topic.id)


class PostCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.id})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.id}),
            data={"content": "Test Message"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(Post.objects.get(content="Test Message"))

    def test_post_session_key(self):
        topic = Topic.objects.get(id=1)
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.id}),
            data={"content": "Test Post"},
        )
        post = Post.objects.get(content="Test Post")
        self.assertEqual(self.client.session.session_key, post.session_key)

    def test_post_approval(self):
        board = Board.objects.get(id=1)
        board.preferences.require_approval = True
        board.preferences.save()
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": 1}), data={"content": "Test Post"}
        )
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.approved, False)
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": 1}),
            data={"content": "Test Post user1"},
        )
        post = Post.objects.get(content="Test Post user1")
        self.assertEqual(post.approved, True)
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": 1}),
            data={"content": "Test Post user2"},
        )
        post = Post.objects.get(content="Test Post user2")
        self.assertEqual(post.approved, False)


class PostUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(
            content="Test Post",
            topic=topic,
        )

    def test_anonymous_permissions(self):
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": "test-board", "topic_pk": 1}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        self.assertEqual(self.client.session.session_key, post.session_key)
        response = self.client.post(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id}),
            data={"content": "Test Post anon NEW"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.get(id=2).content, "Test Post anon NEW")

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(id=1)
        response = self.client.get(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(id=1)
        response = self.client.get(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id}),
            data={"content": "Test Post NEW"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.get(id=1).content, "Test Post NEW")


class PostDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic)

    def test_anonymous_permissions(self):
        response = self.client.post(reverse("boards:post-delete", kwargs={"slug": "test-board", "pk": 1}))
        self.assertEqual(Post.objects.count(), 1)
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": "test-board", "topic_pk": 1}),
            data={"content": "Test Post anon"},
        )
        self.assertEqual(Post.objects.count(), 2)
        response = self.client.post(reverse("boards:post-delete", kwargs={"slug": "test-board", "pk": 2}))
        self.assertEqual(Post.objects.count(), 1)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(id=1)
        response = self.client.post(
            reverse("boards:post-delete", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Post.objects.count(), 1)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(id=1)
        response = self.client.post(
            reverse("boards:post-delete", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 0)


class BoardFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_board_fetch(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-fetch", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["board"], board)


class TopicFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)

    def test_topic_fetch(self):
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-fetch", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["topic"], topic)


class PostFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic, session_key="testing_key", approved=False)

    def test_post_fetch(self):
        post = Post.objects.get(content="Test Post")
        post.approved = True
        post.save()
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post"], post)
        self.assertContains(response, "Test Post", html=True)

    def test_post_fetch_content_anonymous_not_approved(self):
        self.client.get(reverse("boards:board", kwargs={"slug": Board.objects.get(id=1).slug}))
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertNotContains(response, "Test Post", html=True)

    def test_post_fetch_content_other_user_not_approved(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        self.client.get(reverse("boards:board", kwargs={"slug": Board.objects.get(id=1).slug}))
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertNotContains(response, "Test Post", html=True)

    def test_post_fetch_content_owner_not_approved(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertContains(response, "Test Post", html=True)

    def test_post_fetch_content_can_approve_not_approved(self):
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user2.user_permissions.add(Permission.objects.get(codename="can_approve_posts"))
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertContains(response, "Test Post", html=True)


class PostToggleApprovalViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.require_approval = True
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic, session_key="testing_key", approved=False)

    def test_post_toggle_approval_anonymous(self):
        post = Post.objects.get(content="Test Post")
        self.assertFalse(post.approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, f"/accounts/login/?next=/boards/{post.topic.board.slug}/posts/{post.id}/approval/"
        )

    def test_post_toggle_approval_other_user(self):
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(content="Test Post")
        self.assertFalse(post.approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_post_toggle_approval_owner(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(content="Test Post")
        self.assertFalse(post.approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.get(content="Test Post").approved)


class ImageSelectViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        module_dir = os.path.dirname(__file__)
        image_path = os.path.join(module_dir, "images/white.jpg")
        for type, text in IMAGE_TYPE:
            for i in range(5):
                image = Image(
                    type=type,
                    image=SimpleUploadedFile(
                        name=f"{type}-{i}.jpg",
                        content=open(image_path, "rb").read(),
                        content_type="image/jpeg",
                    ),
                    title=f"{text} {i}",
                )
                image.save()

    def test_image_select_anonymous(self):
        for type, text in IMAGE_TYPE:
            response = self.client.get(reverse("boards:image-select", kwargs={"type": type}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, f"/accounts/login/?next=/boards/image_select/{type}/")

    def test_image_select_logged_in(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        for type, text in IMAGE_TYPE:
            response = self.client.get(reverse("boards:image-select", kwargs={"type": type}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["images"].count(), Image.objects.filter(type=type).count())


class QrViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_qr_anonymous(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/boards/{board.slug}/qr/")

    def test_qr_other_user(self):
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_qr_owner(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_qr_staff(self):
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD", is_staff=True)
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
