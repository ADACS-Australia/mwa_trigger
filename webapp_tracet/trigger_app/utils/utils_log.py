import inspect
import logging
from datetime import datetime
from functools import wraps

import pytz  # For UTC timezone


def log_event1(log_location="end", message="", level="debug"):
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
            if log_location == "end" and isinstance(result, dict) and result.get('reached_end', False):
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
                    exc_info=True
                )
                
                if handle_errors:
                    # Handle the error (you can customize this part)
                    context['error'] = str(e)
                    return context
                else:
                    raise  # Re-raise the exception if not handling errors

        return wrapper
    return decorator

def get_caller_info():
    stack = inspect.stack()
    # The caller of the decorated function will be 3 levels up in the stack
    caller = stack[3]
    return caller.filename, caller.lineno

def log_event(log_location="end", message="", level="debug"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("django_json")
            log_method = getattr(logger, level)
            
            def get_context_info():
                context = next((arg for arg in args if isinstance(arg, dict)), None)
                if context is None:
                    context = next((value for value in kwargs.values() if isinstance(value, dict)), {})
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
            if log_location == "end" and isinstance(result, dict) and result.get('reached_end', False):
                log_message("End of")
            
            return result
        return wrapper
    return decorator