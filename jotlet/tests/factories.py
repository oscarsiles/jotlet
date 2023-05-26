import factory
from faker import Faker

fake = Faker()


# Utility Factories
class JSONFactory(factory.DictFactory):
    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        return fake.json(data_columns=[("Name", "name")])
