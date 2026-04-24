from celery import shared_task
from django.utils import timezone

@shared_task
def release_expired_reservations() :
    from .models import Reservation
    
    # Finding all the reserved seats whose expiry timeout has already passed
    expired_reservations = Reservation.objects.filter(
        status = 'RESERVED',
        expires_at__lt = timezone.now()
    )

    count = expired_reservations.count()

    for reservation in expired_reservations:

        # Releasing the seat for letting other users to reserve the seat
        seat = reservation.seat
        seat.is_booked = False
        seat.save()

        # Mark reservation as expired
        reservation.status = 'EXPIRED'
        reservation.save()

    return f'{count} reservations released'