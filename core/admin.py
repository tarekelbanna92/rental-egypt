from django.contrib import admin
from .models import Profile, Listing, Booking

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "city", "host", "price_per_night", "created_at")
    search_fields = ("title", "city", "host__username")
    
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("listing", "guest", "check_in", "check_out", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("listing__title", "guest__username")
