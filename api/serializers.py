from rest_framework import serializers
from .models import MindMap, Page, Node, Edge, Section, Frame, TextAnnotation


# ───────────────────────────── leaf serializers ─────────────────────────────

class NodeSerializer(serializers.ModelSerializer):
    parentId = serializers.SerializerMethodField()
    sectionId = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = ['id', 'label', 'color', 'points', 'parentId',
                  'collapsed', 'sectionId', 'description']

    def get_parentId(self, obj):
        return obj.parent_id  # already a string or None

    def get_sectionId(self, obj):
        return obj.section_id  # already a string or None


class EdgeSerializer(serializers.ModelSerializer):
    sourceId = serializers.CharField(source='source_id')
    targetId = serializers.CharField(source='target_id')
    type = serializers.CharField(source='edge_type')
    sourceShape = serializers.CharField(source='source_shape')
    targetShape = serializers.CharField(source='target_shape')

    class Meta:
        model = Edge
        fields = ['id', 'sourceId', 'targetId', 'type', 'color', 'sourceShape', 'targetShape']


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'title', 'color', 'height', 'width', 'x']


class FrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['id', 'label', 'color', 'x', 'y', 'width', 'height']


class TextAnnotationSerializer(serializers.ModelSerializer):
    fontSize = serializers.IntegerField(source='font_size')
    fontWeight = serializers.CharField(source='font_weight')
    fontStyle = serializers.CharField(source='font_style')
    textDecoration = serializers.CharField(source='text_decoration')

    class Meta:
        model = TextAnnotation
        fields = ['id', 'text', 'x', 'y', 'fontSize', 'color', 'fontWeight', 'fontStyle', 'textDecoration']


# ───────────────────────────── page serializer ──────────────────────────────

class PageSerializer(serializers.ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    edges = EdgeSerializer(many=True, read_only=True)
    sections = SectionSerializer(many=True, read_only=True)
    frames = FrameSerializer(many=True, read_only=True)
    texts = TextAnnotationSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = ['id', 'name', 'nodes', 'edges', 'sections', 'frames', 'texts']


class PageListSerializer(serializers.ModelSerializer):
    """Light-weight page list (no deep nested data)."""
    class Meta:
        model = Page
        fields = ['id', 'name', 'order']


# ───────────────────────────── mindmap serializer ───────────────────────────

class MindMapListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MindMap
        fields = ['id', 'name', 'created_at', 'updated_at']


class MindMapDetailSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)

    class Meta:
        model = MindMap
        fields = ['id', 'name', 'pages', 'created_at', 'updated_at']


# ───────────────────────────── write serializers ────────────────────────────

class BulkPageWriteSerializer(serializers.Serializer):
    """
    Accepts the full pages[] array from the frontend and upserts
    all child objects. This keeps the API simple: one PUT call syncs everything.
    """
    id = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(default='Page 1')
    nodes = serializers.ListField(child=serializers.DictField(), default=list)
    edges = serializers.ListField(child=serializers.DictField(), default=list)
    sections = serializers.ListField(child=serializers.DictField(), default=list)
    frames = serializers.ListField(child=serializers.DictField(), default=list)
    texts = serializers.ListField(child=serializers.DictField(), default=list)


class MindMapWriteSerializer(serializers.Serializer):
    name = serializers.CharField(default='Untitled Mind Map')
    pages = BulkPageWriteSerializer(many=True, default=list)
