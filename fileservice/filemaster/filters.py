from .models import ArchiveFile
from django_filters import rest_framework as rest_framework_filters


class ArchiveFileFilter(rest_framework_filters.FilterSet):
    min_creationdate = rest_framework_filters.DateFilter(name="creationdate", lookup_type='gte')
    max_creationdate = rest_framework_filters.DateFilter(name="creationdate", lookup_type='lte')
    min_modifydate = rest_framework_filters.DateFilter(name="modifydate", lookup_type='gte')
    max_modifydate = rest_framework_filters.DateFilter(name="modifydate", lookup_type='lte')
    
    class Meta:
        model = ArchiveFile
        fields = ['description', 
                  'filename', 
                  'min_creationdate', 
                  'max_creationdate', 
                  'min_modifydate', 
                  'max_modifydate']
