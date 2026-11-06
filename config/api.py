"""Utilitários compartilhados da API REST (versão v1).

Mantém o formato de erro consistente e os endpoints de infraestrutura
(como o health check) usados pelo front React.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """Padroniza o corpo de erro da API.

    Reaproveita o handler padrão do DRF (que já trata status HTTP,
    autenticação e validação) e reembrulha a resposta num envelope único:

        {"error": {"status": <int>, "detail": <dados do DRF>}}

    Erros não tratados pelo DRF seguem o fluxo normal do Django
    (retornando None aqui), respeitando o DEBUG para o 500.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    # Normaliza o caso mais comum ({"detail": "..."}) para não aninhar
    # "detail" dentro de "detail".
    if isinstance(detail, dict) and set(detail.keys()) == {"detail"}:
        detail = detail["detail"]

    response.data = {
        "error": {
            "status": response.status_code,
            "detail": detail,
        }
    }
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Health check simples: GET /api/v1/health/ -> {"status": "ok"}."""
    return Response({"status": "ok"})
