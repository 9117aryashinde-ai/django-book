from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('<int:movie_id>/theaters', views.theater_list, name='theater_list'),

    # we can change the path to this too
    # 'theater/<int:theater_id>/book-seats'
    path('theater/<int:theater_id>/seats/book', views.book_seats, name='book_seats'),
    path('<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('create-order/', views.create_order, name='create_order'),
    path('reserve-seats/', views.reserve_seats, name='reserve_seats'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    # path('mock-successful-payment/<int:reservation_id>/', views.mock_successful_payment, name='mock_successful_payment'),
]