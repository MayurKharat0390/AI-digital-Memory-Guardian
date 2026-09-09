"""memory/urls.py — URL patterns for the memory app"""
from django.urls import path
from . import views

urlpatterns = [
    # Frontend
    path('', views.index, name='index'),

    # API
    path('api/ingest/',              views.IngestView.as_view(),       name='api-ingest'),
    path('api/query/',               views.QueryView.as_view(),        name='api-query'),
    path('api/compare/',             views.CompareView.as_view(),      name='api-compare'),
    path('api/library/',             views.LibraryView.as_view(),      name='api-library'),
    path('api/library/<str:source>/',views.LibraryDeleteView.as_view(),name='api-library-delete'),
]
