# -*- coding: utf-8 -*-
"""
RAG 기반 개인화 문제 생성 서비스 (모듈화된 버전)
모듈화를 통해 디버깅과 유지보수가 쉬워진 구조
"""
import logging
import azure.functions as func
from .rag.rag_orchestrator import RAGOrchestrator


def handle_rag_personalized_generation(req):
    """
    RAG 기반 개인화 문제 생성 처리 (모듈화된 버전)
    이제 RAGOrchestrator를 통해 전체 플로우를 처리합니다.
    """
    orchestrator = RAGOrchestrator()
    return orchestrator.handle_rag_personalized_generation(req)