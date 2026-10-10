from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.permissions import AllowAny
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/", include("comptes.urls")),
    path("api/accounts/", include("comptes.urls")),
    path("api/lenders/", include("preteurs.urls")),
    path("api/invitations/", include("invitations.urls")),
    path("api/borrowers/", include("emprunteurs.urls")),
    path("api/loans/", include("prets.urls")),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)