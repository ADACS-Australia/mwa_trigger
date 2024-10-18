import inspect
import logging
from datetime import datetime
from functools import wraps


def log_event1(log_location="end", message="", level="debug"):
    """
    A decorator that logs events at the start or end of a function execution.

    Args:
        log_location (str): Specifies when to log the event. Can be "start" or "end". Default is "end".
        message (str): Custom message to include in the log. Default is an empty string.
        level (str): Log level to use. Default is "debug".

    Returns:
        function: Decorated function that includes logging functionality.

    The decorator logs function name, custom message, file path, line number, event_id, and trig_id.
    When log_location is "end", it only logs if the function returns a dict with 'reached_end' set to True.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("django_json")
            log_method = getattr(logger, level)

            pathname = inspect.getfile(func)
            lineno = inspect.getsourcelines(func)[1]

            # Log at the start if specified
            if log_location == "start":
                context = next((arg for arg in args[:2] if isinstance(arg, dict)), None)
                if context is None:
                    context = kwargs.get('context', {})
                # If event_id is not in context, try to get it from the event object
                event = context.get("event", context.get("latestVoevent", {}))
                event_id = context.get("event_id") or getattr(event, 'id', None)
                trig_id = context.get("trig_id") or getattr(event, 'trig_id', None)

                log_method(
                    f"Start of {func.__name__}: {message}",
                    extra={
                        "logpathname": pathname,
                        "loglineno": lineno,
                        "function": func.__name__,
                        "event_id": event_id,
                        "trig_id": trig_id,
                    },
                )

            result = func(*args, **kwargs)

            # Log at the end if specified and reached_end is True
            if (
                log_location == "end"
                and isinstance(result, dict)
                and result.get('reached_end', False)
            ):
                context = result
                event = context.get("event", context.get("latestVoevent", {}))
                event_id = context.get("event_id") or getattr(event, 'id', None)
                trig_id = context.get("trig_id") or getattr(event, 'trig_id', None)

                log_method(
                    f"End of {func.__name__}: {message}",
                    extra={
                        "logpathname": pathname,
                        "loglineno": lineno,
                        "function": func.__name__,
                        "event_id": event_id,
                        "trig_id": trig_id,
                    },
                )

            return result

        return wrapper

    return decorator


def log_event_with_error(message, level="debug", handle_errors=True):
    """
    A decorator that logs events and handles errors in function execution.

    Args:
        message (str): Custom message to include in the log.
        level (str): Log level to use. Default is "debug".
        handle_errors (bool): If True, catches and logs exceptions, returning a context with error info.
                              If False, re-raises the exception. Default is True.

    Returns:
        function: Decorated function that includes logging and error handling functionality.

    The decorator logs at the start of the function, upon successful completion, and in case of an error.
    It includes function name, custom message, file path, line number, event_id, and trig_id in the logs.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = kwargs.get('context', {})

            event = context.get("event", context.get("latestVoevent", {}))
            event_id = context.get("event_id") or getattr(event, 'id', None)
            trig_id = context.get("trig_id") or getattr(event, 'trig_id', None)

            logger = logging.getLogger("django_json")
            log_method = getattr(logger, level.lower(), logger.debug)

            pathname = inspect.getfile(func)
            lineno = inspect.getsourcelines(func)[1]

            try:
                # Log before executing the function
                log_method(
                    f"Starting {func.__name__}: {message}",
                    extra={
                        "logpathname": pathname,
                        "loglineno": lineno,
                        "function": f"{func.__module__}.{func.__name__}",
                        "event_id": event_id,
                        "trig_id": trig_id,
                    },
                )

                # Execute the original function
                result = func(*args, **kwargs)

                # Log success if the function reached the end
                if isinstance(result, dict) and result.get('reached_end', False):
                    log_method(
                        f"Successfully completed {func.__name__}: {message}",
                        extra={
                            "logpathname": pathname,
                            "loglineno": lineno,
                            "function": f"{func.__module__}.{func.__name__}",
                            "event_id": event_id,
                            "trig_id": trig_id,
                        },
                    )

                return result

            except Exception as e:
                # Always log the error
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    extra={
                        "logpathname": pathname,
                        "loglineno": lineno,
                        "function": f"{func.__module__}.{func.__name__}",
                        "event_id": event_id,
                        "trig_id": trig_id,
                    },
                    exc_info=True,
                )

                if handle_errors:
                    # Handle the error (you can customize this part)
                    context['error'] = str(e)
                    return context
                else:
                    raise  # Re-raise the exception if not handling errors

        return wrapper

    return decorator


import inspect
import logging
from functools import wraps


def get_caller_info():
    """
    Retrieves information about the caller of the decorated function.

    Returns:
        tuple: A tuple containing the filename and line number of the caller.
    """
    stack = inspect.stack()
    # The caller of the decorated function will be 3 levels up in the stack
    caller = stack[3]
    return caller.filename, caller.lineno


def log_event(log_location="end", message="", level="debug"):
    """
    A decorator that logs events at the start or end of a function execution.

    Args:
        log_location (str): Specifies when to log the event. Can be "start" or "end". Default is "end".
        message (str): Custom message to include in the log. Default is an empty string.
        level (str): Log level to use. Default is "debug".

    Returns:
        function: Decorated function that includes logging functionality.

    This decorator is an improved version of log_event1. It logs function name, custom message,
    file path, line number, event_id, and trig_id. When log_location is "end", it only logs
    if the function returns a dict with 'reached_end' set to True.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("django_json")
            log_method = getattr(logger, level)

            def get_context_info():
                context = next((arg for arg in args if isinstance(arg, dict)), None)
                if context is None:
                    context = next(
                        (value for value in kwargs.values() if isinstance(value, dict)),
                        {},
                    )
                event = context.get("event", context.get("latestVoevent", {}))
                event_id = context.get("event_id") or getattr(event, 'id', None)
                trig_id = context.get("trig_id") or getattr(event, 'trig_id', None)
                return context, event_id, trig_id

            def log_message(prefix):
                pathname, lineno = get_caller_info()
                _, event_id, trig_id = get_context_info()
                log_method(
                    f"{prefix} {func.__name__}: {message}",
                    extra={
                        "logpathname": pathname,
                        "loglineno": lineno,
                        "function": func.__name__,
                        "event_id": event_id,
                        "trig_id": trig_id,
                    },
                )

            # Log at the start if specified
            if log_location == "start":
                log_message("Start of")

            result = func(*args, **kwargs)

            # Log at the end if specified and reached_end is True
            if (
                log_location == "end"
                and isinstance(result, dict)
                and result.get('reached_end', False)
            ):
                log_message("End of")

            return result

        return wrapper

    return decorator
