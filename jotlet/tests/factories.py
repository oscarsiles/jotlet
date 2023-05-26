import json

import factory
import faker

fake = faker.Faker()


class JotletDict(dict):
    pass


class JSONStringFactory(factory.Factory):
    class Meta:
        model = str

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return json.dumps(fake.pydict(allowed_types=[str, int, float, bool]))


class JSONFactory(factory.Factory):
    class Meta:
        model = JotletDict

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return json.loads(json.dumps(fake.pydict(allowed_types=[str, int, float, bool])))
