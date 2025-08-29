from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField

class Profile(models.Model):
    class Role(models.TextChoices):
        HOST = 'HOST', 'Host'
        GUEST = 'GUEST', 'Guest'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.GUEST)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class Listing(models.Model):
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    image = CloudinaryField('image', blank=True, null=True)  # Cloudinary upload
    image_url = models.URLField(blank=True)                  # optional fallback for old data
    capacity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['city', '-created_at']),
        ]

    @property
    def cover_image(self):
        cover = self.images.filter(is_cover=True).first()
        return cover or self.images.first()


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')
    is_cover = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return f"Image for {self.listing.title}"

    @staticmethod
    def compute_next_order(listing: 'Listing') -> int:
        last = listing.images.order_by('-sort_order').first()
        return (last.sort_order + 1) if last else 0


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        DECLINED = 'DECLINED', 'Declined'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    guests_count = models.PositiveIntegerField(default=1)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.listing.title} ({self.check_in} → {self.check_out})"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['listing', 'status', 'check_in', 'check_out']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        # Date order validation
        if self.check_in and self.check_out and self.check_in >= self.check_out:
            raise ValidationError("Check-out must be after check-in.")
        # Overlap validation against approved bookings
        if self.listing_id and self.check_in and self.check_out:
            qs = Booking.objects.filter(
                listing=self.listing,
                status=Booking.Status.APPROVED,
                check_in__lt=self.check_out,
                check_out__gt=self.check_in,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Selected dates are unavailable.")
