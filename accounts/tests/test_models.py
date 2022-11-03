class TestUserProfile:
    def test_user_profile_string(self, user):
        assert str(user.profile) == f"{user.username}'s profile"
