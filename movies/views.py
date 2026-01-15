from ntpath import join
from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

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
            except IntegrityError:
                error_seats.append(seat.seat_number)
        if error_seats:
            error_message = f"The following seats are already booked:{',',join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {'theater':theaters, 'seats':seats, 'error':'No seat selected'})
        return redirect('profile')
    return render(request, 'movies/seat_selection.html', {'theaters':theaters, 'seats':seats})