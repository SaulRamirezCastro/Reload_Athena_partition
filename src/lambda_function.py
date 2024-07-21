from src.reload_athena import ReloadHivePartition


def lambda_handler(event, context):
    """"Call the class Reload
    """

    if event.get('prefix'):
        prefix_event = event.get('prefix')
        athena_reload = ReloadHivePartition(prefix=prefix_event)
        athena_reload.reload()
    else:
        athena_reload = ReloadHivePartition()
        athena_reload.reload()
