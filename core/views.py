from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Q
from django.contrib import messages
from .models import Listing, Booking, Profile, ListingImage
from .forms import SignUpForm, ListingForm, BookingForm, ListingImageUploadForm
from django.core.paginator import Paginator
from datetime import datetime
from django.views.decorators.http import require_POST


DATE_FMT = "%Y-%m-%d"

def home(request):
    # New Airbnb-style params
    destination = request.GET.get('destination', '').strip()
    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    guests = request.GET.get('guests', '').strip()

    # (optional) keep your old free-text search
    q = request.GET.get('q', '').strip()

    listings = (Listing.objects
                .all()
                .order_by('-created_at')
                .select_related('host')
                .prefetch_related('images'))

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

    # capacity filter if guests provided (guard if column not yet migrated)
    if guests.isdigit():
        try:
            listings = listings.filter(capacity__gte=int(guests))
        except Exception:
            # If DB doesn't have the column yet, skip filtering to avoid 500
            pass

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
        form = ListingForm(request.POST, request.FILES)  # handle cover image upload
        if form.is_valid():
            listing = form.save(commit=False)
            listing.host = request.user
            listing.save()
            # handle optional gallery images at creation
            images = request.FILES.getlist('images')
            if images:
                for f in images[:10]:
                    ListingImage.objects.create(
                        listing=listing,
                        image=f,
                        sort_order=ListingImage.compute_next_order(listing),
                    )
            messages.success(request, 'Listing created!')
            return redirect('listing_detail', pk=listing.pk)
    else:
        form = ListingForm()  # GET request

    return render(request, 'core/create_listing.html', {'form': form})



def listing_detail(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    form = BookingForm()
    image_form = ListingImageUploadForm()
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
    return render(request, 'core/listing_detail.html', { 'listing': listing, 'form': form, 'image_form': image_form })


@login_required
def upload_listing_images(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if request.user.profile.role != Profile.Role.HOST or listing.host != request.user:
        messages.error(request, 'Only the host can upload photos to this listing.')
        return redirect('listing_detail', pk=pk)
    if request.method == 'POST':
        form = ListingImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = form.cleaned_data['images']
            created = 0
            for f in files:
                ListingImage.objects.create(
                    listing=listing,
                    image=f,
                    sort_order=ListingImage.compute_next_order(listing),
                )
                created += 1
            messages.success(request, f'Uploaded {created} image(s).')
        else:
            for err in form.errors.get('__all__', []):
                messages.error(request, err)
    return redirect('listing_detail', pk=pk)

@require_POST
@login_required
def reorder_listing_images(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if request.user.profile.role != Profile.Role.HOST or listing.host != request.user:
        messages.error(request, 'Only the host can modify this listing.')
        return redirect('listing_detail', pk=pk)
    order_str = request.POST.get('order', '').strip()
    if not order_str:
        messages.error(request, 'No order provided.')
        return redirect('listing_detail', pk=pk)
    try:
        image_ids = [int(x) for x in order_str.split(',') if x.strip()]
    except ValueError:
        messages.error(request, 'Invalid order data.')
        return redirect('listing_detail', pk=pk)
    # Fetch only images of this listing and ensure ids match
    images = list(ListingImage.objects.filter(listing=listing, id__in=image_ids))
    if len(images) != len(image_ids):
        messages.error(request, 'Some images were not found for this listing.')
        return redirect('listing_detail', pk=pk)
    # Apply sort order according to provided list
    id_to_image = {img.id: img for img in images}
    for idx, img_id in enumerate(image_ids):
        img = id_to_image[img_id]
        img.sort_order = idx
        img.is_cover = (idx == 0)
        img.save(update_fields=['sort_order', 'is_cover'])
    messages.success(request, 'Image order updated. Cover set to first image.')
    return redirect('listing_detail', pk=pk)
@login_required
def set_cover_image(request, pk, image_id):
    listing = get_object_or_404(Listing, pk=pk)
    if request.user.profile.role != Profile.Role.HOST or listing.host != request.user:
        messages.error(request, 'Only the host can modify this listing.')
        return redirect('listing_detail', pk=pk)
    img = get_object_or_404(ListingImage, pk=image_id, listing=listing)
    ListingImage.objects.filter(listing=listing, is_cover=True).update(is_cover=False)
    img.is_cover = True
    img.save(update_fields=['is_cover'])
    messages.success(request, 'Cover photo updated.')
    return redirect('listing_detail', pk=pk)

@login_required
def delete_listing_image(request, pk, image_id):
    listing = get_object_or_404(Listing, pk=pk)
    if request.user.profile.role != Profile.Role.HOST or listing.host != request.user:
        messages.error(request, 'Only the host can modify this listing.')
        return redirect('listing_detail', pk=pk)
    img = get_object_or_404(ListingImage, pk=image_id, listing=listing)
    img.delete()
    messages.info(request, 'Image deleted.')
    return redirect('listing_detail', pk=pk)

@login_required
def my_listings(request):
    if request.user.profile.role != Profile.Role.HOST:
        messages.error(request, 'Only hosts can view this page.')
        return redirect('home')
    listings = (Listing.objects
                .filter(host=request.user)
                .order_by('-created_at')
                .prefetch_related('images'))
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

@require_POST
@login_required
def approve_booking(request, pk):
    if request.user.profile.role != Profile.Role.HOST:
        messages.error(request, 'Only hosts can modify bookings.')
        return redirect('home')
    booking = get_object_or_404(Booking, pk=pk, listing__host=request.user)
    # final overlap check before approval
    overlaps = Booking.objects.filter(
        listing=booking.listing,
        status=Booking.Status.APPROVED,
        check_in__lt=booking.check_out,
        check_out__gt=booking.check_in,
    ).exclude(pk=booking.pk).exists()
    if overlaps:
        messages.error(request, 'Selected dates are unavailable.')
    else:
        booking.status = Booking.Status.APPROVED
        booking.save()
        messages.success(request, 'Booking approved.')
    return redirect('host_bookings')

@require_POST
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
