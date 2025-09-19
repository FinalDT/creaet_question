import azure.functions as func
from modules.question_service import handle_create_question
from modules.connection_service import handle_test_connections
from modules.bulk_service import handle_bulk_generation

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="create_question", methods=["GET"])
def create_question(req: func.HttpRequest) -> func.HttpResponse:
    return handle_create_question(req)


@app.route(route="test_connections")
def test_connections(req: func.HttpRequest) -> func.HttpResponse:
    return handle_test_connections(req)


@app.route(route="bulk_generate", methods=["GET"])
def bulk_generate(req: func.HttpRequest) -> func.HttpResponse:
    return handle_bulk_generation(req)