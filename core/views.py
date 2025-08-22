from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Q
from django.contrib import messages

from .models import Listing, Booking, Profile
from .forms import SignUpForm, ListingForm, BookingForm
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime


DATE_FMT = "%Y-%m-%d"

def home(request):
    # New Airbnb-style params
    destination = request.GET.get('destination', '').strip()
    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    guests = request.GET.get('guests', '').strip()

    # (optional) keep your old free-text search
    q = request.GET.get('q', '').strip()

    listings = Listing.objects.all().order_by('-created_at')

    # destination dropdown filter
    if destination:
        listings = listings.filter(city__iexact=destination)  # exact city from dropdown

    # optional keyword search (title/desc/city)
    if q:
        listings = listings.filter(
            Q(title__icontains=q) | Q(city__icontains=q) | Q(description__icontains=q)
        )

    # date filtering: exclude listings that have an APPROVED overlapping booking
    check_in = check_out = None
    if check_in_str and check_out_str:
        try:
            check_in = datetime.strptime(check_in_str, DATE_FMT).date()
            check_out = datetime.strptime(check_out_str, DATE_FMT).date()
            if check_in < check_out:
                listings = listings.exclude(
                    bookings__status=Booking.Status.APPROVED,
                    bookings__check_in__lt=check_out,
                    bookings__check_out__gt=check_in,
                )
        except ValueError:
            # bad date format: ignore dates
            pass

    # NOTE: we don’t have a "max guests" field on Listing yet,
    # so we collect "guests" for the UI but can’t filter capacity.
    # (We can add a capacity field later if you want.)

    # build city list for dropdown
    cities = (Listing.objects
              .values_list('city', flat=True)
              .distinct()
              .order_by('city'))

    # paginate
    page = request.GET.get('page', 1)
    paginator = Paginator(listings, 9)
    page_obj = paginator.get_page(page)

    return render(request, 'core/home.html', {
        'listings': page_obj.object_list,
        'page_obj': page_obj,
        'cities': cities,
        'destination': destination,
        'check_in': check_in_str,
        'check_out': check_out_str,
        'guests': guests,
        'q': q,  # keep if you want the keyword box too
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
        form = ListingForm(request.POST, request.FILES)  # <-- add request.FILES here
    if form.is_valid():
        listing = form.save(commit=False)
        listing.host = request.user
        listing.save()
        messages.success(request, 'Listing created!')
        return redirect('listing_detail', pk=listing.pk)

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
