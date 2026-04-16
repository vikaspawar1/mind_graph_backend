"""
MindMap Tree-structured data models for PostgreSQL.
Stores the mind-map data in a normalised, tree-first schema.
"""

from django.db import models
import uuid


class MindMap(models.Model):
    """A named mind-map document that contains one or more pages."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, default="Untitled Mind Map")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class Page(models.Model):
    """A page / canvas within a MindMap."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mindmap = models.ForeignKey(MindMap, on_delete=models.CASCADE, related_name='pages')
    name = models.CharField(max_length=255, default="Page 1")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.mindmap.name} > {self.name}"


class Node(models.Model):
    """
    A mind-map node. Stored as an adjacency list to represent the tree.
    `parent` is NULL for root nodes.
    """
    id = models.CharField(max_length=64, primary_key=True)  # keep frontend IDs
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='nodes')
    label = models.CharField(max_length=1024, default="Node")
    color = models.CharField(max_length=32, default="#94A3B8")
    points = models.IntegerField(default=3)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE,
        related_name='children'
    )
    collapsed = models.BooleanField(default=False)
    section = models.ForeignKey(
        'Section', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='nodes'
    )
    # Rich-text description stored as JSON blocks
    description = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.label} ({self.id})"

    def get_ancestors(self):
        """Return all ancestors of this node as a list (bottom → top)."""
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """Return all descendant nodes recursively."""
        result = []
        for child in self.children.all():
            result.append(child)
            result.extend(child.get_descendants())
        return result


class Edge(models.Model):
    """An explicit edge / connection between two nodes (non-tree associations)."""
    EDGE_TYPE_CHOICES = [('direct', 'Direct'), ('indirect', 'Indirect')]
    SHAPE_CHOICES = [('none', 'None'), ('line-arrow', 'Arrow'), ('triangle-arrow', 'Triangle'), ('circle', 'Circle')]

    id = models.CharField(max_length=64, primary_key=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='edges')
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='outgoing_edges')
    target = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='incoming_edges')
    edge_type = models.CharField(max_length=16, choices=EDGE_TYPE_CHOICES, default='direct')
    color = models.CharField(max_length=32, default="#94A3B8")
    source_shape = models.CharField(max_length=32, choices=SHAPE_CHOICES, default='none')
    target_shape = models.CharField(max_length=32, choices=SHAPE_CHOICES, default='none')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('source', 'target')]

    def __str__(self):
        return f"{self.source} → {self.target}"


class Section(models.Model):
    """A coloured column/section grouping nodes on the canvas."""
    id = models.CharField(max_length=64, primary_key=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255, default="Section")
    color = models.CharField(max_length=32, default="#0EA5E9")
    height = models.FloatField(default=400.0)
    width = models.FloatField(null=True, blank=True)
    x = models.FloatField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title


class Frame(models.Model):
    """A freehand rectangular frame / annotation area on the canvas."""
    id = models.CharField(max_length=64, primary_key=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='frames')
    label = models.CharField(max_length=255, default="Frame")
    color = models.CharField(max_length=32, default="#E2E8F0")
    x = models.FloatField(default=0.0)
    y = models.FloatField(default=0.0)
    width = models.FloatField(default=200.0)
    height = models.FloatField(default=150.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label


class TextAnnotation(models.Model):
    """A free-floating text annotation on the canvas."""
    FONT_WEIGHT_CHOICES = [('normal', 'Normal'), ('bold', 'Bold')]
    FONT_STYLE_CHOICES = [('normal', 'Normal'), ('italic', 'Italic')]
    TEXT_DECORATION_CHOICES = [('none', 'None'), ('underline', 'Underline')]

    id = models.CharField(max_length=64, primary_key=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='texts')
    text = models.TextField(default="New Text")
    x = models.FloatField(default=0.0)
    y = models.FloatField(default=0.0)
    font_size = models.IntegerField(default=16)
    color = models.CharField(max_length=32, default="#334155")
    font_weight = models.CharField(max_length=10, choices=FONT_WEIGHT_CHOICES, default='normal')
    font_style = models.CharField(max_length=10, choices=FONT_STYLE_CHOICES, default='normal')
    text_decoration = models.CharField(max_length=16, choices=TEXT_DECORATION_CHOICES, default='none')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]
