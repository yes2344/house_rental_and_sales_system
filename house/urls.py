from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin as django_admin
from django.http import HttpResponseRedirect
from django.views.static import serve
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path('api/v1/', include('house.api_urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    path('admin/', django_admin.site.urls),
    path('user/', include('user.urls')),
    path('admin-portal/', include('admin.urls')),
    path('', lambda request: HttpResponseRedirect('/user/')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA_FILES:
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
