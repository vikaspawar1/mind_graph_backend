from django.contrib import admin
from .models import MindMap, Page, Node, Edge, Section, Frame, TextAnnotation


class NodeInline(admin.TabularInline):
    model = Node
    fields = ['id', 'label', 'color', 'points', 'parent', 'collapsed']
    extra = 0
    show_change_link = True


class EdgeInline(admin.TabularInline):
    model = Edge
    fields = ['id', 'source', 'target', 'edge_type', 'color']
    extra = 0


class SectionInline(admin.TabularInline):
    model = Section
    fields = ['id', 'title', 'color', 'height', 'width']
    extra = 0


class PageInline(admin.TabularInline):
    model = Page
    fields = ['id', 'name', 'order']
    extra = 0
    show_change_link = True


@admin.register(MindMap)
class MindMapAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']
    inlines = [PageInline]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['name', 'mindmap', 'order', 'created_at']
    list_filter = ['mindmap']
    inlines = [NodeInline, EdgeInline, SectionInline]


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ['label', 'id', 'page', 'parent', 'points', 'collapsed']
    list_filter = ['page__mindmap']
    search_fields = ['label', 'id']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'page', 'color', 'height']


@admin.register(Frame)
class FrameAdmin(admin.ModelAdmin):
    list_display = ['label', 'page', 'x', 'y', 'width', 'height']


@admin.register(TextAnnotation)
class TextAnnotationAdmin(admin.ModelAdmin):
    list_display = ['text', 'page', 'x', 'y', 'font_size']
