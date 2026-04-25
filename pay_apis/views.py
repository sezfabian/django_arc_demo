from django.http import JsonResponse
from django_arc_monitize_api.decorators import monetize

async def free_view(request):
    return JsonResponse({'message': 'Hello, World! This is a free view.'})

@monetize('0.001')
async def cheap_view(request):
    return JsonResponse({
        "message": "Hello World (paid cheap view)",
        "status": "success",
        "architect": "Fabian",
        "payer": getattr(request, "payer", ""),
        "price_usdc": '0.001',
    })

@monetize('0.1')
async def expensive_view(request):
    return JsonResponse({
        "message": "Hello World (paid expensive view)",
        "status": "success",
        "architect": "Fabian",
        "payer": getattr(request, "payer", ""),
        "price_usdc": '0.1',
    })