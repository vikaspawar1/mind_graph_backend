from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health),
    path('mindmaps/', views.mindmap_list),
    path('mindmaps/<str:pk>/', views.mindmap_detail),
    path('mindmaps/<str:mindmap_pk>/pages/<str:page_pk>/', views.page_detail),
]
