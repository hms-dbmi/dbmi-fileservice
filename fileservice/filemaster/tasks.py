from __future__ import absolute_import

from celery import shared_task

#from filemaster.tasks import add
#add.delay(2, 2)

@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)