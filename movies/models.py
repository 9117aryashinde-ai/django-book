from django.db import models

# django creates user model by default including the username, email, password
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta # Allows us to perform arithmetic operations on time

# models.py define the tables in the database
# Movie, Theater, Seat and Booking all define tables in the database.

class Movie(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='movies/')
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True) # optional
    genre = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    trailer_url = models.TextField(blank=True, null=True) # optional

    def __str__(self):
        return self.name
    
class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='theaters')
    time = models.DateTimeField()

    pricing = models.IntegerField(default=200)

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'

class Seat(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='seats') # which seat belongs to which theater
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False) # checking if the seat is booked or not

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat, blank=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    # totalAmount = models.IntegerField()
    booked_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('CONFIRMED', 'Confirmed'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING'
    )

    def __str__(self):
        return f'Booking by {self.user.username} at {self.theater.name}'

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)

    # Razorpay Info
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    # Storing the payment amount
    amount = models.IntegerField(default=500) # Amount stored in paise

    # Payment status
    status = models.CharField(
        max_length=20,
        choices=[
            ('CREATED', 'Created'),
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
        ],
        default='CREATED'
    )

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f'Payment {self.razorpay_order_id} - {self.status}'
    
class Reservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)

    # STATUS Field
    STATUS_CHOICES = [
        ('RESERVED', 'Reserved'), # seat is currently held, payment pending
        ('EXPIRED', 'Expired'), # payment not done, timeout expired
        ('COMPLETED', 'Completed'), # payment done, seat confirmed
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RESERVED')

    # Expiry
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f'Reservation by {self.user.username} for {self.seat.seat_number} - {self.status}'