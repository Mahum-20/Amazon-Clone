from .models import Category

def navbar_data(request):
    categories = Category.objects.all()
    return {'categories': categories}