"""
URL configuration for agri_notice_platform project.
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.http import JsonResponse
from django.views.generic import RedirectView


def health_check(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='notices:notice_list', permanent=False), name='home'),
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('notices/', include('apps.notices.urls')),
    path('api/', include('rest_framework.urls')),
]

# Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
