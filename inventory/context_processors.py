from .models import Category

def categories_processor(request):
    """Add categories to the template context for the admin dashboard."""
    if request.path.startswith('/admin/'):
        return {
            'categories': Category.objects.all().order_by('name')
        }
    return {} 