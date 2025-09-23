# -*- coding: utf-8 -*-
"""
Azure Functions 개인화 문제 생성 API 핸들러 (뷰 기반)
"""
import azure.functions as func
import json
import logging
from ..services.view_service import handle_view_generation


def handle_create_by_view(req: func.HttpRequest) -> func.HttpResponse:
    """뷰 기반 개인화 문제 생성 API 핸들러"""
    logging.info('create_by_view API 호출됨')

    try:
        # GET과 POST 모두 동일하게 문제 생성 (bulk_generate와 완전 동일)
        return handle_view_generation(req)

    except Exception as e:
        logging.error(f"create_by_view API 오류: {str(e)}")

        return func.HttpResponse(
            json.dumps({"error": f"내부 서버 오류: {str(e)}"}, ensure_ascii=False),
            status_code=500,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )