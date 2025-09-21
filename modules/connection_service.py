# -*- coding: utf-8 -*-
import os
from .database import get_sql_connection
from .ai_service import test_ai_connection
from .responses import create_success_response
from .debug import print_connection_test_header, print_connection_test_summary


def handle_test_connections(req):
    """연결 테스트 요청 처리"""
    print_connection_test_header()

    results = {"openai_status": "❌ FAILED", "sql_status": "❌ FAILED"}

    # OpenAI 연결 테스트
    print("\n📡 Testing Azure OpenAI connection...")
    try:
        print(f"   - Endpoint: {os.environ.get('AOAI_ENDPOINT', 'Not set')}")
        print(f"   - Deployment: {os.environ.get('AOAI_DEPLOYMENT', 'Not set')}")
        print(f"   - API Key: {'[설정됨]' if os.environ.get('AOAI_KEY') else '[설정안됨]'}")

        ai_success, ai_message = test_ai_connection()
        if ai_success:
            results["openai_status"] = "[성공] SUCCESS"
            print("   [성공] Azure OpenAI connection: SUCCESS")
        else:
            results["openai_error"] = ai_message
            print(f"   ❌ Azure OpenAI connection: FAILED - {ai_message}")
    except Exception as e:
        results["openai_error"] = str(e)
        print(f"   ❌ Azure OpenAI connection: FAILED - {str(e)}")

    # SQL 연결 테스트
    print("\n[SQL 서버 테스트] 연결 확인 중...")
    try:
        conn_str = os.environ.get('SQL_CONNECTION', 'Not set')
        print(f"   - Connection string: {'[설정됨]' if conn_str != 'Not set' else '[설정안됨]'}")

        conn = get_sql_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            results["sql_status"] = "[성공] SUCCESS"
            print("   [성공] SQL Server connection: SUCCESS")
        else:
            print("   ❌ SQL Server connection: FAILED (No connection object)")
    except Exception as e:
        results["sql_error"] = str(e)
        print(f"   ❌ SQL Server connection: FAILED - {str(e)}")

    print_connection_test_summary(results)
    return create_success_response(results)