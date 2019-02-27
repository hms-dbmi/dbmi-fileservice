from .models import ArchiveFile
from django_filters import rest_framework as rest_framework_filters


class ArchiveFileFilter(rest_framework_filters.FilterSet):
    min_creationdate = rest_framework_filters.DateFilter(field_name="creationdate", lookup_expr='gte')
    max_creationdate = rest_framework_filters.DateFilter(field_name="creationdate", lookup_expr='lte')
    min_modifydate = rest_framework_filters.DateFilter(field_name="modifydate", lookup_expr='gte')
    max_modifydate = rest_framework_filters.DateFilter(field_name="modifydate", lookup_expr='lte')
    
    class Meta:
        model = ArchiveFile
        fields = ['description', 
                  'filename', 
                  'min_creationdate', 
                  'max_creationdate', 
                  'min_modifydate', 
                  'max_modifydate']
