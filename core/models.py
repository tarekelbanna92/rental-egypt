from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField

class Listing(models.Model):
    title = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    # OLD: image_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='listings/', blank=True, null=True)

    def __str__(self):
        return self.title


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
    image = CloudinaryField('image', blank=True, null=True)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

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
