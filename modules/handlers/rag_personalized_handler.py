# -*- coding: utf-8 -*-
"""
RAG 기반 개인화 문제 생성 API 핸들러
"""
import azure.functions as func
import json
import logging
from ..services.rag_personalized_service import handle_rag_personalized_generation


def handle_create_by_view_rag_personalized(req: func.HttpRequest) -> func.HttpResponse:
    """RAG 기반 개인화 문제 생성 API 핸들러"""
    logging.info('create_by_view_rag_personalized API 호출됨')

    try:
        # GET과 POST 모두 지원
        return handle_rag_personalized_generation(req)

    except Exception as e:
        logging.error(f"create_by_view_rag_personalized API 오류: {str(e)}")

        return func.HttpResponse(
            json.dumps({"error": f"내부 서버 오류: {str(e)}"}, ensure_ascii=False),
            status_code=500,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )