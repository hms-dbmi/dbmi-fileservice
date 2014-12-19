import django_filters
from .models import ArchiveFile


class ArchiveFileFilter(django_filters.FilterSet):
    min_creationdate = django_filters.DateFilter(name="creationdate", lookup_type='gte')
    max_creationdate = django_filters.DateFilter(name="creationdate", lookup_type='lte')
    min_modifydate = django_filters.DateFilter(name="modifydate", lookup_type='gte')
    max_modifydate = django_filters.DateFilter(name="modifydate", lookup_type='lte')
    
    class Meta:
        model = ArchiveFile
        fields = ['description', 
                  'filename', 
                  'min_creationdate', 
                  'max_creationdate', 
                  'min_modifydate', 
                  'max_modifydate']
