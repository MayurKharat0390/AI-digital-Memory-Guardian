"""
memory/views.py
---------------
Django REST API — all endpoints for the Memory Guardian.

Endpoints:
  GET  /              → serve index.html
  POST /api/ingest/   → chunk + embed + store document
  POST /api/query/    → semantic search + RAG
  POST /api/compare/  → keyword vs. semantic side-by-side
  GET  /api/library/  → list all sources
  DELETE /api/library/<source>/ → delete a source
"""
from __future__ import annotations

import os
import time

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from pipeline.chunker       import chunk_text
from pipeline.embedder      import get_model, embed_texts, embed_query
from pipeline.vector_store  import (
    add_documents, semantic_search, update_retrieval_stats,
    list_sources, delete_source, collection_count,
)
from pipeline.keyword_search import keyword_search
from pipeline.rag            import generate_answer


# ── Serve the SPA ─────────────────────────────────────────────────────────────

def index(request):
    """Serve the single-page frontend."""
    return render(request, 'index.html')


# ── /api/ingest/ ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class IngestView(APIView):
    """
    POST /api/ingest/
    Accepts: multipart/form-data with 'file' (optional) and/or 'text' + 'name'
    Returns: {"status": "ok", "chunks_added": N, "source": "..."}
    """

    def post(self, request):
        source_name = None
        raw_text    = None

        # ── Mode 1: File upload ───────────────────────────────────────────────
        if 'file' in request.FILES:
            uploaded = request.FILES['file']
            source_name = uploaded.name
            raw_text = uploaded.read().decode('utf-8', errors='replace')

        # ── Mode 2: Pasted text ───────────────────────────────────────────────
        elif 'text' in request.data and request.data['text'].strip():
            raw_text    = request.data['text']
            source_name = request.data.get('name', 'pasted_text') or 'pasted_text'

        else:
            return Response(
                {'error': 'Provide either a file or text field.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Stage 1: Chunk
        chunks = chunk_text(raw_text)
        if not chunks:
            return Response(
                {'error': 'No content could be extracted from the input.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Stage 2: Embed (local model)
        model = get_model()
        embeddings = embed_texts([c['text'] for c in chunks], model=model)

        # Stage 3: Store in ChromaDB
        n_added = add_documents(
            chunks=chunks,
            embeddings=[e.tolist() for e in embeddings],
            source=source_name,
            upload_ts=time.time(),
        )

        return Response({
            'status':       'ok',
            'source':       source_name,
            'chunks_added': n_added,
            'total_chunks': collection_count(),
        })


# ── /api/query/ ───────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class QueryView(APIView):
    """
    POST /api/query/
    Body: {"query": "...", "top_k": 5, "api_key": "sk-ant-...", "model": "..."}
    Returns: {"results": [...], "answer": "...", "usage": {...}}
    """

    def post(self, request):
        query   = request.data.get('query', '').strip()
        top_k   = int(request.data.get('top_k', 5))
        api_key = request.data.get('api_key', '').strip() or os.environ.get('ANTHROPIC_API_KEY', '')
        model   = request.data.get('model', 'claude-3-5-haiku-20241022')

        if not query:
            return Response({'error': 'Query is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if collection_count() == 0:
            return Response({'error': 'No documents ingested yet.'}, status=status.HTTP_400_BAD_REQUEST)

        # Stage 1: Embed query (local)
        embedding_model = get_model()
        q_vec = embed_query(query, model=embedding_model)

        # Stage 2: Semantic search + re-ranking
        results = semantic_search(q_vec, top_k=top_k)

        if results:
            update_retrieval_stats([r['id'] for r in results])

        # Stage 3: RAG via Claude (optional — only if API key provided)
        answer = None
        usage  = None
        if api_key and results:
            try:
                answer, usage = generate_answer(
                    query=query,
                    chunks=results,
                    api_key=api_key,
                    model=model,
                )
            except Exception as e:
                answer = f"[Claude API error: {e}]"

        # Serialize (remove non-JSON-safe objects)
        serialized = [{
            'text':        r['text'],
            'source':      r['metadata'].get('source', '?'),
            'chunk_index': r['metadata'].get('chunk_index', 0),
            'similarity':  r['similarity'],
            'final_score': r['final_score'],
            'recency':     r['recency'],
            'frequency':   r['frequency'],
            'retrieved_n': int(r['metadata'].get('retrieval_count', 0)),
        } for r in results]

        return Response({
            'query':   query,
            'results': serialized,
            'answer':  answer,
            'usage':   usage,
        })


# ── /api/compare/ ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class CompareView(APIView):
    """
    POST /api/compare/
    Body: {"query": "...", "top_k": 5, "api_key": "...", "model": "..."}
    Returns: {"keyword": [...], "semantic": [...], "answer": "..."}
    """

    def post(self, request):
        query   = request.data.get('query', '').strip()
        top_k   = int(request.data.get('top_k', 5))
        api_key = request.data.get('api_key', '').strip() or os.environ.get('ANTHROPIC_API_KEY', '')
        model   = request.data.get('model', 'claude-3-5-haiku-20241022')

        if not query:
            return Response({'error': 'Query is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Keyword search
        kw_results = keyword_search(query, top_k=top_k)

        # Semantic search
        embedding_model = get_model()
        q_vec    = embed_query(query, model=embedding_model)
        sem_results = semantic_search(q_vec, top_k=top_k)
        if sem_results:
            update_retrieval_stats([r['id'] for r in sem_results])

        # RAG on semantic results
        answer = None
        if api_key and sem_results:
            try:
                answer, _ = generate_answer(
                    query=query,
                    chunks=sem_results,
                    api_key=api_key,
                    model=model,
                )
            except Exception as e:
                answer = f"[Claude API error: {e}]"

        return Response({
            'query':    query,
            'keyword':  [{
                'text':          r['text'],
                'source':        r['metadata'].get('source', '?'),
                'kw_score':      r['kw_score'],
                'matched_terms': r['matched_terms'],
            } for r in kw_results],
            'semantic': [{
                'text':        r['text'],
                'source':      r['metadata'].get('source', '?'),
                'final_score': r['final_score'],
                'similarity':  r['similarity'],
            } for r in sem_results],
            'answer': answer,
        })


# ── /api/library/ ─────────────────────────────────────────────────────────────

class LibraryView(APIView):
    """
    GET  /api/library/           → list sources
    DELETE /api/library/<src>/   → delete source
    """

    def get(self, request):
        sources = list_sources()
        sources.sort(key=lambda s: s['upload_ts'], reverse=True)
        # Format timestamps for display
        import datetime
        for s in sources:
            ts = s.get('upload_ts', 0)
            s['upload_date'] = (
                datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                if ts else 'unknown'
            )
        return Response({
            'sources':     sources,
            'total_chunks': collection_count(),
        })


@method_decorator(csrf_exempt, name='dispatch')
class LibraryDeleteView(APIView):
    """DELETE /api/library/<source>/"""

    def delete(self, request, source):
        n = delete_source(source)
        return Response({'deleted': n, 'source': source})
