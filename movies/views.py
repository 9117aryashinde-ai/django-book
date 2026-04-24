from datetime import timedelta
from ntpath import join
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Payment, Theater, Seat, Booking, Reservation
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.core.mail import EmailMessage, send_mail # django's built in function to send mails
from django.conf import settings # allows us to access EMAIL_HOST_USER (sender email)
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
import razorpay
from django.db import transaction
from django.utils import timezone
import hmac
import hashlib

# Create your views here.

def movie_list(request):
    search_query = request.GET.get('search')
    if search_query:

        # This line will provide the name of all the movies containing the search text
        # Movie.objects.filter is used for fetching the movies from the database
        movies = Movie.objects.filter(name__icontains=search_query) # i_contains represents case-insensitive search
    else:
        # if no search is done show all movies
        movies = Movie.objects.all()

    genre = request.GET.get('genre')
    language = request.GET.get('language')

    if genre:
        # movies.filter is used for refining the movies that we already have
        movies = movies.filter(genre__iexact=genre) # __iexact refers to case insensitive exact match

    if language:
        movies = movies.filter(language__iexact=language)

    # sending data to the template
    return render(request, 'movies/movie_list.html', {'movies':movies})

def theater_list(request, movie_id):
    # This view basically finds the theaters for a particular movie_id

    movie = get_object_or_404(Movie, id=movie_id)
    theater = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {'movie':movie, 'theaters':theater})

@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theaters = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theaters).order_by('seat_number')
    if request.method == 'POST':
        selected_Seats = request.POST.getlist('seats')

        if not selected_Seats:
            return render(request, 'movies/seat_selection.html', {'theater':theaters, 'seats':seats, 'error':'No seat selected'})

        seat_id = selected_Seats[0]
        seat = get_object_or_404(Seat, id=seat_id, theater=theaters)

        # Check if seat is already booked:
        if seat.is_booked:
            return render(request, 'movies/seat_selection.html', {
                'theater':theaters, 
                'seats':seats, 
                'error':'Seat already booked'
            })

        return render(request, 'movies/payment_page.html', {
            'seat_id':seat_id,
            'theater_id':theaters.id,
            'movie_id':theaters.movie.id,
            'amount':theaters.pricing
        })
    return render(request, 'movies/seat_selection.html', {'theaters':theaters, 'seats':seats})

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theater = Theater.objects.first()
    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'theater': theater
    })

# Razorpay Payment Integration View
# This endpoint will receive data and process payment logic
def create_order(request):
    if request.method == "POST" :

        # Getting data from the frontend:
        seat_id = request.POST.get("seat_id")
        theater_id = request.POST.get("theater_id")
        movie_id = request.POST.get("movie_id")

        user = request.user

        # Fetching the exact details from the database
        seat = Seat.objects.get(id=seat_id)
        theater = Theater.objects.get(id=theater_id)
        movie = Movie.objects.get(id=movie_id)

        # Check if there are any active reservations
        reservation = Reservation.objects.filter(
            user = user,
            seat = seat,
            status = 'RESERVED',
            expires_at__gt = timezone.now()
        ).first()

        if not reservation:
            return JsonResponse({'error': 'No active reservation found. Please book the seat again'}, status=400)

        if reservation.is_expired():
            return JsonResponse({'error': 'Reservation is expired. Please select the seat again.'}, status=400)
                
        # Converting Rupees to paise since Razorpay deals with paise
        amount = theater.pricing * 100

        # Connecting Razorpay with the backend
        # Initializing client
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY)
        )

        # Creating razorpay order
        order = client.order.create({
            "amount":amount,
            "currency":"INR",
            "payment_capture": 1,
        })

        # Link Razorpay order to existing booking
        booking = reservation.booking
        Payment.objects.create(
            user = user,
            booking = booking,
            razorpay_order_id = order['id'],
            amount = amount,
            status = 'CREATED',
        )

        # Returning data to the frontend
        return JsonResponse({
            "order_id":order["id"],
            "amount":amount,
            "booking_id":booking.id,
            "reservation_id":reservation.id,
            "key":settings.RAZORPAY_KEY_ID
        })
    
def payment_success(request):
    if request.method == 'POST':

        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        reservation_id = request.POST.get('reservation_id')

        # Verify payment signature
        body = razorpay_order_id + "|" + razorpay_payment_id
        expected_signature = hmac.new(
            settings.RAZORPAY_SECRET_KEY.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        if expected_signature != razorpay_signature:
            return JsonResponse({'error': 'Invalid Payment Signature'}, status=400)
        
        try:
            reservation = Reservation.objects.get(id=reservation_id)

            # Check if reservation is still valid
            if reservation.is_expired():
                return JsonResponse({'error': 'Resevation is expired'}, status=400)
            
            booking = reservation.booking
            booking.status = 'CONFIRMED'
            booking.save()

            reservation.status = 'COMPLETED'
            reservation.save()

            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'SUCCESS'
            payment.save()

            return JsonResponse({
                "message":"Payment successful! Booking Confirmed",
                "booking_id": booking.id
            }, status=200)
        
        except Reservation.DoesNotExist:
            return JsonResponse({'error':'Reservation not found'}, status=404)

def reserve_seat(request, seat_id):
    # allow only POST requests
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    # allow only logged in users
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'}, status=401)
    
    try:

        # If booking fails the everthing gets rolled back automatically
        with transaction.atomic():
            # Locking the seat row
            seat = Seat.objects.select_for_update().get(id=seat_id)

            # Check seat availability
            if seat.is_booked:
                return JsonResponse({'error': 'Seat already booked'}, status=400)
            
            # Check if seat is already reserved
            active_reservation = Reservation.objects.filter(
                seat = seat,
                status = 'RESERVED',
                expires_at__gt = timezone.now()
            ).first()

            if active_reservation:
                return JsonResponse({'error': 'Seat already reserved'}, status=400)
            
            # Create booking
            # booking = Booking.objects.create(
            #     user = request.user,
            #     seat = seat,
            #     movie = seat.theater.movie,
            #     theater = seat.theater,
            #     status = 'PENDING',
            # )

            booking, created = Booking.objects.get_or_create(
                seat = seat,
                defaults={
                    'user': request.user,
                    'movie': seat.theater.movie,
                    'theater': seat.theater,
                    'status': 'PENDING'
                }
            )

            # Reset booking if not created
            if not created:
                booking.user = request.user
                booking.status = 'PENDING'
                booking.save()

            # Create Reservation
            reservation = Reservation.objects.create(
                user = request.user,
                seat = seat,
                booking = booking,
                expires_at = timezone.now() + timedelta(minutes = 5)
            )

            seat.is_booked = True
            seat.save()

        return JsonResponse({
            'message': 'Seat reserved successfully',
            'reservation_id':reservation.id,
            'booking_id':booking.id,
            'expires_at':reservation.expires_at,
        }, status=200)
    
    except Seat.DoesNotExist:
        return JsonResponse({'error': 'Seat not found'}, status=404)

def payment_failed(request):
    if request.method == 'POST':
        reservation_id = request.POST.get("reservation_id")

        try:
            reservation = Reservation.objects.get(id=reservation_id)

            seat = reservation.seat
            seat.is_booked = False
            seat.save()

            reservation.status = 'EXPIRED'
            reservation.save()

            booking = reservation.booking
            booking.status = 'FAILED'
            booking.save()

            return JsonResponse({'message': 'Seat relesead successfully'}, status=200)
        
        except Reservation.DoesNotExist:
            return JsonResponse({'error': 'Reservation not found'}, status=404)

# View for mocking successful payment
def mock_successful_payment(request, reservation_id):
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        # Confirm booking
        booking = reservation.booking
        booking.status = 'CONFIRMED'
        booking.save()

        # Save Reservation
        reservation.status = 'COMPLETED'
        reservation.save()

        # Update seat
        seat = reservation.seat
        seat.is_booked = True
        seat.save()

        send_booking_confirmation(
            user=reservation.user,
            booking=booking,
            seat=seat,
            movie=booking.movie,
            theater=booking.theater
        )

        return JsonResponse({'message': 'Mock Payment Successful', 'booking_id':booking.id}, status=200)
    
    except Reservation.DoesNotExist:
        return JsonResponse({'error': 'Reservation not found'}, status=404)
    
def send_booking_confirmation(user, booking, seat, movie, theater):
    subject = f'Booking Confirmed - {movie.name} | BookMySeat'

    html_content = render_to_string('emails/booking_confirmation.html', {
        'username': user.username,
        'movie_name': movie.name,
        'theater_name': theater.name,
        'seats': [seat.seat_number]
    })

    email = EmailMessage(
        subject=subject,
        body=html_content,
        to=[user.email]
    )
    email.content_subtype = 'html'
    email.send()