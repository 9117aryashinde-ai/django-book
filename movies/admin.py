from django.contrib import admin
from .models import Movie, Theater, Seat, Booking, Payment, Reservation

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['name', 'rating', 'cast', 'description']

@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'movie', 'time']

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'is_booked']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'theater', 'booked_at']

    # def get_seats(self, obj):
    #     return ", ".join([seat.seat_number for seat in obj.seats.all()])
    
    # get_seats.short_description = "Seats"

admin.site.register(Reservation)