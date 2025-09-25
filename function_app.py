import azure.functions as func
from modules.services.question_service import handle_create_question
from modules.services.connection_service import handle_test_connections
from modules.services.bulk_service import handle_bulk_generation
from modules.handlers.create_by_view_handler import handle_create_by_view
from modules.handlers.personalized_handler import handle_create_personalized
from modules.handlers.rag_personalized_handler import handle_create_by_view_rag_personalized

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="create_question", methods=["GET", "POST"])
def create_question(req: func.HttpRequest) -> func.HttpResponse:
    return handle_create_question(req)


@app.route(route="test_connections", methods=["GET", "POST"])
def test_connections(req: func.HttpRequest) -> func.HttpResponse:
    return handle_test_connections(req)


@app.route(route="bulk_generate", methods=["GET", "POST"])
def bulk_generate(req: func.HttpRequest) -> func.HttpResponse:
    return handle_bulk_generation(req)


@app.route(route="create_by_view", methods=["GET", "POST"])
def create_by_view(req: func.HttpRequest) -> func.HttpResponse:
    return handle_create_by_view(req)


@app.route(route="create_personalized", methods=["GET", "POST"])
def create_personalized(req: func.HttpRequest) -> func.HttpResponse:
    return handle_create_personalized(req)


@app.route(route="create_by_view_rag_personalized", methods=["GET", "POST"])
def create_by_view_rag_personalized(req: func.HttpRequest) -> func.HttpResponse:
    return handle_create_by_view_rag_personalized(req)
