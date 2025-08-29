from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('listing/new/', views.create_listing, name='create_listing'),
    path('listing/<int:pk>/', views.listing_detail, name='listing_detail'),
    path('listing/<int:pk>/images/upload/', views.upload_listing_images, name='upload_listing_images'),
    path('listing/<int:pk>/images/reorder/', views.reorder_listing_images, name='reorder_listing_images'),
    path('listing/<int:pk>/images/<int:image_id>/cover/', views.set_cover_image, name='set_cover_image'),
    path('listing/<int:pk>/images/<int:image_id>/delete/', views.delete_listing_image, name='delete_listing_image'),

    path('host/listings/', views.my_listings, name='my_listings'),
    path('host/bookings/', views.host_bookings, name='host_bookings'),
    path('booking/<int:pk>/approve/', views.approve_booking, name='approve_booking'),
    path('booking/<int:pk>/decline/', views.decline_booking, name='decline_booking'),

    path('bookings/', views.my_bookings, name='my_bookings'),
]
