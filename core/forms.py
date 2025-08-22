from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Listing, Booking

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.Role.choices, initial=Profile.Role.GUEST)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "role")

class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ("title", "description", "city", "address", "price_per_night", "image")

class DateInput(forms.DateInput):
    input_type = 'date'

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("check_in", "check_out", "guests_count", "message")
        widgets = {
            'check_in': DateInput(),
            'check_out': DateInput(),
            'message': forms.Textarea(attrs={'rows': 3})
        }
