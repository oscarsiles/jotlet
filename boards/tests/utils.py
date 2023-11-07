import factory


def create_image(image_format):
    return factory.Faker("image", image_format=image_format).evaluate({}, None, {"locale": "en"})
