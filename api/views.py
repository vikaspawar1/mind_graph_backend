"""
API views for the MindGraph application.
All mutations use a bulk-sync strategy: the frontend sends its complete
state and the view reconciles the DB to match it.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import uuid

from .models import MindMap, Page, Node, Edge, Section, Frame, TextAnnotation
from .serializers import (
    MindMapListSerializer, MindMapDetailSerializer,
    MindMapWriteSerializer, PageSerializer
)

# ════════════════════════════════════════════════════════════════════════

def _sync_page(page: Page, page_data: dict) -> None:
    """
    Reconcile the DB state of `page` to exactly match `page_data`.
    Runs inside a transaction.
    """
    incoming_node_ids: set[str] = set()
    incoming_edge_ids: set[str] = set()
    incoming_section_ids: set[str] = set()
    incoming_frame_ids: set[str] = set()
    incoming_text_ids: set[str] = set()


    for idx, s in enumerate(page_data.get('sections', [])):
        sid = s.get('id') or f"sec_{idx}"
        incoming_section_ids.add(sid)
        Section.objects.update_or_create(
            id=sid,
            defaults={
                'page': page,
                'title': s.get('title', 'Section'),
                'color': s.get('color', '#0EA5E9'),
                'height': float(s.get('height', 400)),
                'width': float(s['width']) if s.get('width') is not None else None,
                'x': float(s['x']) if s.get('x') is not None else None,
                'order': idx,
            }
        )
    page.sections.exclude(id__in=incoming_section_ids).delete()

   
    nodes_payload = page_data.get('nodes', [])
    parent_map: dict[str, str | None] = {}  # node_id → parentId

    for n in nodes_payload:
        nid = n['id']
        incoming_node_ids.add(nid)
        parent_map[nid] = n.get('parentId')
        sec_id = n.get('sectionId')

        Node.objects.update_or_create(
            id=nid,
            defaults={
                'page': page,
                'label': n.get('label', 'Node'),
                'color': n.get('color', '#94A3B8'),
                'points': int(n.get('points', 3)),
                'collapsed': bool(n.get('collapsed', False)),
                'section_id': sec_id if sec_id and Section.objects.filter(id=sec_id).exists() else None,
                'description': n.get('description'),
                'parent': None,  # set in second pass
            }
        )

    for nid, parent_id in parent_map.items():
        if parent_id and parent_id in incoming_node_ids:
            Node.objects.filter(id=nid, page=page).update(parent_id=parent_id)
        else:
            Node.objects.filter(id=nid, page=page).update(parent=None)

    page.nodes.exclude(id__in=incoming_node_ids).delete()

  
    for e in page_data.get('edges', []):
        eid = e['id']
        src_id = e.get('sourceId', '')
        tgt_id = e.get('targetId', '')
        if not Node.objects.filter(id=src_id).exists():
            continue
        if not Node.objects.filter(id=tgt_id).exists():
            continue

        incoming_edge_ids.add(eid)
        Edge.objects.update_or_create(
            id=eid,
            defaults={
                'page': page,
                'source_id': src_id,
                'target_id': tgt_id,
                'edge_type': e.get('type', 'direct'),
                'color': e.get('color', '#94A3B8'),
                'source_shape': e.get('sourceShape', 'none'),
                'target_shape': e.get('targetShape', 'none'),
            }
        )
    page.edges.exclude(id__in=incoming_edge_ids).delete()


    for f in page_data.get('frames', []):
        fid = f['id']
        incoming_frame_ids.add(fid)
        Frame.objects.update_or_create(
            id=fid,
            defaults={
                'page': page,
                'label': f.get('label', 'Frame'),
                'color': f.get('color', '#E2E8F0'),
                'x': float(f.get('x', 0)),
                'y': float(f.get('y', 0)),
                'width': float(f.get('width', 200)),
                'height': float(f.get('height', 150)),
            }
        )
    page.frames.exclude(id__in=incoming_frame_ids).delete()

    # 5. Text annotations
    for t in page_data.get('texts', []):
        tid = t['id']
        incoming_text_ids.add(tid)
        TextAnnotation.objects.update_or_create(
            id=tid,
            defaults={
                'page': page,
                'text': t.get('text', ''),
                'x': float(t.get('x', 0)),
                'y': float(t.get('y', 0)),
                'font_size': int(t.get('fontSize', 16)),
                'color': t.get('color', '#334155'),
                'font_weight': t.get('fontWeight', 'normal'),
                'font_style': t.get('fontStyle', 'normal'),
                'text_decoration': t.get('textDecoration', 'none'),
            }
        )
    page.texts.exclude(id__in=incoming_text_ids).delete()


# MindMap CRUD

@api_view(['GET', 'POST'])
def mindmap_list(request):
    """
    GET  /api/mindmaps/           → list all mind maps
    POST /api/mindmaps/           → create a new mind map (with pages/nodes)
    """
    if request.method == 'GET':
        maps = MindMap.objects.all()
        return Response(MindMapListSerializer(maps, many=True).data)

    # POST
    write_ser = MindMapWriteSerializer(data=request.data)
    write_ser.is_valid(raise_exception=True)
    data = write_ser.validated_data

    with transaction.atomic():
        mm = MindMap.objects.create(name=data['name'])

        for order, page_data in enumerate(data.get('pages', [])):
            page = Page.objects.create(
                mindmap=mm,
                name=page_data.get('name', f"Page {order + 1}"),
                order=order,
            )
            _sync_page(page, page_data)

    detail_ser = MindMapDetailSerializer(mm)
    return Response(detail_ser.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def mindmap_detail(request, pk):
    """
    GET    /api/mindmaps/<pk>/    → full mind map with all pages
    PUT    /api/mindmaps/<pk>/    → full replace (sync entire state)
    PATCH  /api/mindmaps/<pk>/    → rename only
    DELETE /api/mindmaps/<pk>/    → delete
    """
    mm = get_object_or_404(MindMap, pk=pk)

    if request.method == 'GET':
        return Response(MindMapDetailSerializer(mm).data)

    if request.method == 'DELETE':
        mm.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == 'PATCH':
        name = request.data.get('name')
        if name:
            mm.name = name
            mm.save(update_fields=['name', 'updated_at'])
        return Response(MindMapDetailSerializer(mm).data)

    # PUT – full sync
    write_ser = MindMapWriteSerializer(data=request.data)
    write_ser.is_valid(raise_exception=True)
    data = write_ser.validated_data

    with transaction.atomic():
        mm.name = data['name']
        mm.save(update_fields=['name', 'updated_at'])

        incoming_page_ids: set[str] = set()

        for order, page_data in enumerate(data.get('pages', [])):
            pid = page_data.get('id')
            is_valid_uuid = False
            if pid:
                try:
                    uuid.UUID(str(pid))
                    is_valid_uuid = True
                except ValueError:
                    is_valid_uuid = False

            if pid and is_valid_uuid:
                incoming_page_ids.add(pid)
                page, _ = Page.objects.get_or_create(
                    id=pid, mindmap=mm,
                    defaults={'name': page_data.get('name', 'Page'), 'order': order}
                )
                page.name = page_data.get('name', 'Page')
                page.order = order
                page.save(update_fields=['name', 'order'])
            else:
                page = Page.objects.create(
                    mindmap=mm,
                    name=page_data.get('name', 'Page'),
                    order=order,
                )
                pid = str(page.id)
                incoming_page_ids.add(pid)
            _sync_page(page, page_data)

        mm.pages.exclude(id__in=incoming_page_ids).delete()

    return Response(MindMapDetailSerializer(mm).data)


# Single-page sync

@api_view(['GET', 'PUT'])
def page_detail(request, mindmap_pk, page_pk):
    """
    GET /api/mindmaps/<mm_pk>/pages/<page_pk>/  → single page data
    PUT /api/mindmaps/<mm_pk>/pages/<page_pk>/  → sync single page
    """
    mm = get_object_or_404(MindMap, pk=mindmap_pk)
    page = get_object_or_404(Page, pk=page_pk, mindmap=mm)

    if request.method == 'GET':
        return Response(PageSerializer(page).data)

    with transaction.atomic():
        page.name = request.data.get('name', page.name)
        page.save(update_fields=['name'])
        _sync_page(page, request.data)

    return Response(PageSerializer(page).data)


# Health-check

@api_view(['GET'])
def health(request):
    return Response({'status': 'ok', 'service': 'MindGraph API'})
