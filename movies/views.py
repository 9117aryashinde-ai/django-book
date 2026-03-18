from ntpath import join
from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.core.mail import send_mail # django's built in function to send mails
from django.conf import settings # allows us to access EMAIL_HOST_USER (sender email)
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

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
    seats = Seat.objects.filter(theater=theaters)
    if request.method == 'POST':
        selected_Seats = request.POST.getlist('seats')
        error_seats = []
        if not selected_Seats:
            return render(request, 'movies/seat_selection.html', {'theater':theaters, 'seats':seats, 'error':'No seat selected'})
        newly_booked_seats = []
        for seat_id in selected_Seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theaters)
            if seat.is_booked:
                error_seats.append(seat.seat_number)
                continue
            try:
                Booking.objects.create(
                    user = request.user,
                    seat = seat,
                    movie = theaters.movie,
                    theater = theaters
                )
                seat.is_booked = True
                seat.save()
                newly_booked_seats.append(seat.seat_number)
            except IntegrityError:
                error_seats.append(seat.seat_number)
         
        if error_seats:
            error_message = f"The following seats are already booked:{',',join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {'theater':theaters, 'seats':seats, 'error':'No seat selected'})
        else:
            # Preparing email details

            email_context = {
                "username" : request.user.username,
                "movie_name" : theaters.movie.name, 
                "theater_name" : theaters.name,
                "seats" : newly_booked_seats,
            }

            subject = "Booking Confirmation"
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [request.user.email]

            html_content = render_to_string(
                "emails/booking_confirmation.html",
                email_context
            )

            # This block prepares the letter, the letter is not sent yet
            # This block creates the plain text version
            # This is for email clients that do not support html
            email = EmailMultiAlternatives(
                subject,
                "Your booking is confirmed", # this string can be used to add the plain text message for the clients that do not support html
                from_email,
                recipient_list
            )

            # This line tells that this line has an html version
            email.attach_alternative(html_content, "text/html")

            # while sending the mail both the plain text one and the html one are sent the client now decides which one it supports.
            email.send()

            
            # This block is commented because this block sends email in the text form (no style)
            # message = (
            #     f"Hello {request.user.username}, \n\n"
            #     f"Your Booking is Confirmed!\n\n"
            #     f"Movie: {theaters.movie.name}\n"
            #     f"Theater: {theaters.name}\n"
            #     f"Seats: {', '.join(newly_booked_seats)}\n\n"
            #     f"Enjoy your movie!"
            # )

            # send_mail(
            #     subject,
            #     message,
            #     from_email,
            #     recipient_list,
            #     fail_silently=False
            # )
        return redirect('profile')
    return render(request, 'movies/seat_selection.html', {'theaters':theaters, 'seats':seats})

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theater = Theater.objects.first()
    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'theater': theater
    })