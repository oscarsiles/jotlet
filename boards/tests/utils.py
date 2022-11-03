import factory


def create_image(type):
    return factory.Faker("image", image_format=type).evaluate({}, None, {"locale": "en"})
