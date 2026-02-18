import time

def format_milliseconds(ms):
    """Format milliseconds to HH:MM:SS"""
    seconds = ms / 1000.0
    return time.strftime('%H:%M:%S', time.gmtime(seconds))
