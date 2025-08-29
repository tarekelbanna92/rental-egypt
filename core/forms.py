from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Listing, Booking, ListingImage
class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.Role.choices, initial=Profile.Role.GUEST)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "role")

class ListingForm(forms.ModelForm):
    MAX_IMAGE_MB = 5

    def clean_image(self):
        img = self.cleaned_data.get('image')
        if img and hasattr(img, 'size'):
            if img.size > self.MAX_IMAGE_MB * 1024 * 1024:
                raise forms.ValidationError(f"Image must be <= {self.MAX_IMAGE_MB}MB.")
        return img
    class Meta:
        model = Listing
        fields = ("title", "description", "city", "address", "price_per_night", "capacity", "image")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "price_per_night": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

class DateInput(forms.DateInput):
    input_type = 'date'

class BookingForm(forms.ModelForm):
    def clean(self):
        cleaned = super().clean()
        check_in = cleaned.get('check_in')
        check_out = cleaned.get('check_out')
        if check_in and check_out and check_in >= check_out:
            raise forms.ValidationError("Check-out must be after check-in.")
        return cleaned
    class Meta:
        model = Booking
        fields = ("check_in", "check_out", "guests_count", "message")
        widgets = {
            'check_in': DateInput(attrs={"class": "form-control"}),
            'check_out': DateInput(attrs={"class": "form-control"}),
            'guests_count': forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            'message': forms.Textarea(attrs={'rows': 3, "class": "form-control"}),
        }


class ListingImageUploadForm(forms.Form):
    images = forms.FileField(widget=MultiFileInput(attrs={"class": "form-control", "accept": "image/*", "multiple": True}), required=True)
    MAX_FILES = 10
    MAX_IMAGE_MB = 5

    def clean(self):
        cleaned = super().clean()
        files = self.files.getlist('images')
        if not files:
            raise forms.ValidationError("Please select at least one image.")
        if len(files) > self.MAX_FILES:
            raise forms.ValidationError(f"You can upload up to {self.MAX_FILES} images at once.")
        for f in files:
            if hasattr(f, 'size') and f.size > self.MAX_IMAGE_MB * 1024 * 1024:
                raise forms.ValidationError(f"Each image must be <= {self.MAX_IMAGE_MB}MB.")
        cleaned['images'] = files
        return cleaned
