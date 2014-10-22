import datetime
from haystack import indexes
from .models import ArchiveFile


class ArchiveFileIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    description = indexes.CharField(model_attr='description')
    filename = indexes.CharField(model_attr='filename')
    uuid = indexes.CharField(model_attr='uuid')
    metadata = indexes.CharField(model_attr='metadata')
    tags = indexes.CharField()
    tag_list = indexes.MultiValueField()
    locations = indexes.CharField()
    locations_list = indexes.MultiValueField()

    owner = indexes.CharField(model_attr='owner')
    creation_date = indexes.DateTimeField(model_attr='creationdate')
    modify_date = indexes.DateTimeField(model_attr='modifydate')

    def get_model(self):
        return ArchiveFile

    def prepare_tags(self, obj):
        return ' '.join([tag.name for tag in obj.tags.all()])

    def prepare_tag_list(self, obj):
        return [tag.name for tag in obj.tags.all()]

    def prepare_locations(self, obj):
        return ' '.join([location.url for location in obj.locations.all()])

    def prepare_locations_list(self, obj):
        return [location.url for location in obj.locations.all()]


    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()