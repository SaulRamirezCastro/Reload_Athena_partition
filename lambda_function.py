# -*- coding: utf-8 -*-
""" 
Created by saul ramirez at 9/24/2020
Updated by Saul Ramirez at 27/4/2021

"""

from reload_athena import Reload


def lambda_handler(event, context):
    """"Call the class Reload
    """

    if event.get('prefix'):
        prefix_event = event.get('prefix')
        athena_reload = Reload(prefix=prefix_event)
        athena_reload.reload()
    else:
        athena_reload = Reload()
        athena_reload.reload()
