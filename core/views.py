from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Q
from django.contrib import messages

from .models import Listing, Booking, Profile
from .forms import SignUpForm, ListingForm, BookingForm
from django.core.paginator import Paginator
from django.db.models import Q

def home(request):
    q = request.GET.get('q', '').strip()
    city = request.GET.get('city', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    page = request.GET.get('page', 1)

    listings = Listing.objects.all().order_by('-created_at')

    if q:
        listings = listings.filter(
            Q(title__icontains=q) | Q(city__icontains=q) | Q(description__icontains=q)
        )
    if city:
        listings = listings.filter(city__icontains=city)
    if min_price:
        listings = listings.filter(price_per_night__gte=min_price)
    if max_price:
        listings = listings.filter(price_per_night__lte=max_price)

    paginator = Paginator(listings, 9)  # 9 cards per page
    page_obj = paginator.get_page(page)

    return render(request, 'core/home.html', {
        'listings': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'city': city,
        'min_price': min_price,
        'max_price': max_price,
    })



# Auth

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data['email']
            user.save()
            # ensure profile exists via signal, then set role
            profile = user.profile
            profile.role = form.cleaned_data['role']
            profile.save()
            login(request, user)
            messages.success(request, 'Welcome to Rental Egypt!')
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'core/signup.html', { 'form': form })

# Listings

@login_required
def create_listing(request):
    if request.user.profile.role != Profile.Role.HOST:
        messages.error(request, 'Only hosts can create listings.')
        return redirect('home')
    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.host = request.user
            listing.save()
            messages.success(request, 'Listing created!')
            return redirect('listing_detail', pk=listing.pk)
    else:
        form = ListingForm()
    return render(request, 'core/create_listing.html', { 'form': form })


def listing_detail(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    form = BookingForm()
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Please sign in to request a booking.')
            return redirect('login')
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.listing = listing
            booking.guest = request.user
            # Ensure no overlap with approved bookings
            overlaps = Booking.objects.filter(
                listing=listing,
                status=Booking.Status.APPROVED,
                check_in__lt=booking.check_out,
                check_out__gt=booking.check_in,
            ).exists()
            if overlaps:
                messages.error(request, 'Selected dates are unavailable.')
            else:
                booking.save()
                messages.success(request, 'Booking request sent!')
                return redirect('my_bookings')
    return render(request, 'core/listing_detail.html', { 'listing': listing, 'form': form })

@login_required
def my_listings(request):
    if request.user.profile.role != Profile.Role.HOST:
        messages.error(request, 'Only hosts can view this page.')
        return redirect('home')
    listings = Listing.objects.filter(host=request.user).order_by('-created_at')
    return render(request, 'core/my_listings.html', { 'listings': listings })

@login_required
def host_bookings(request):
    if request.user.profile.role != Profile.Role.HOST:
        messages.error(request, 'Only hosts can view this page.')
        return redirect('home')
    bookings = Booking.objects.filter(listing__host=request.user).select_related('listing', 'guest')
    return render(request, 'core/host_bookings.html', { 'bookings': bookings })

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(guest=request.user).select_related('listing')
    return render(request, 'core/my_bookings.html', { 'bookings': bookings })

@login_required
def approve_booking(request, pk):
    if request.user.profile.role != Profile.Role.HOST:
        messages.error(request, 'Only hosts can modify bookings.')
        return redirect('home')
    booking = get_object_or_404(Booking, pk=pk, listing__host=request.user)
    booking.status = Booking.Status.APPROVED
    booking.save()
    messages.success(request, 'Booking approved.')
    return redirect('host_bookings')

@login_required
def decline_booking(request, pk):
    if request.user.profile.role != Profile.Role.HOST:
        messages.error(request, 'Only hosts can modify bookings.')
        return redirect('home')
    booking = get_object_or_404(Booking, pk=pk, listing__host=request.user)
    booking.status = Booking.Status.DECLINED
    booking.save()
    messages.info(request, 'Booking declined.')
    return redirect('host_bookings')
