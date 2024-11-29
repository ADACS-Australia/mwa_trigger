import functools
import inspect
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ..models.telescopesettings import (
    ATCATelescopeSettings,
    BaseTelescopeSettings,
    MWATelescopeSettings,
)


def log_parameters(prefix: str = ""):
    """
    Decorator that logs function parameters to a JSON file.

    Args:
        prefix (str): Optional prefix for the log filename
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create data directory if it doesn't exist
            data_dir = Path("prop_api/data/function_logs")
            data_dir.mkdir(parents=True, exist_ok=True)

            # Get function details
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            func_name = func.__name__

            # Get parameter names from function signature
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            # Create dictionary of args and kwargs
            args_dict = {}

            # Handle args
            for i, arg in enumerate(args):
                if i < len(param_names):
                    args_dict[param_names[i]] = _serialize_param(arg)
                else:
                    args_dict[f"arg_{i}"] = _serialize_param(arg)

            # Handle kwargs
            kwargs_dict = {k: _serialize_param(v) for k, v in kwargs.items()}

            # Combine all parameters
            params_dict = {
                "timestamp": timestamp,
                "function_name": func_name,
                "args": args_dict,
                "kwargs": kwargs_dict,
                "module": func.__module__,
                "docstring": func.__doc__,
            }

            # Create filename
            filename = (
                f"{prefix}_{func_name}_{timestamp}.json"
                if prefix
                else f"{func_name}_{timestamp}.json"
            )
            filepath = data_dir / filename

            # Save to JSON file
            try:
                with open(filepath, 'w') as f:
                    json.dump(params_dict, f, indent=2, default=str)
                print(f"Parameters logged to: {filepath}")
            except Exception as e:
                print(f"Error saving parameters: {str(e)}")

            # Call the original function
            result = func(*args, **kwargs)

            # Optionally, save the result too
            try:
                result_dict = {
                    "parameters": params_dict,
                    "result": _serialize_param(result),
                }
                result_filepath = data_dir / f"result_{filename}"
                with open(result_filepath, 'w') as f:
                    json.dump(result_dict, f, indent=2, default=str)
            except Exception as e:
                print(f"Error saving result: {str(e)}")

            return result

        return wrapper

    return decorator


def _serialize_param(param: Any) -> Any:
    """Helper function to serialize parameters"""
    try:
        # Handle common types that need special serialization
        if hasattr(param, 'dict'):
            # For Pydantic models or objects with dict() method
            return param.dict()
        elif hasattr(param, '__dict__'):
            # For general objects
            return {
                "_type": param.__class__.__name__,
                "attributes": {k: str(v) for k, v in param.__dict__.items()},
            }
        elif isinstance(param, (list, tuple, set)):
            return [_serialize_param(item) for item in param]
        elif isinstance(param, dict):
            return {str(k): _serialize_param(v) for k, v in param.items()}
        else:
            # Try direct serialization
            json.dumps(param)
            return param
    except:
        # If all else fails, convert to string
        return str(param)


import functools
import json
from datetime import datetime
from pathlib import Path


def get_project_root():
    """Get absolute path to project root"""
    current_file = Path(__file__)  # This file's location
    return (
        current_file.parent.parent.parent
    )  # Go up three levels from utils/decorators.py


def convert_to_nested_dict(obj: Any) -> Any:
    """
    Recursively convert an object and its nested attributes to a dictionary.
    Handles special cases like Pydantic models, TelescopeSettings, and custom objects.
    """
    try:
        # Handle None
        if obj is None:
            return None

        # Handle Pydantic models
        if hasattr(obj, 'dict'):
            return obj.dict()

        # Handle lists, tuples, and sets
        if isinstance(obj, (list, tuple, set)):
            return [convert_to_nested_dict(item) for item in obj]

        # Handle dictionaries
        if isinstance(obj, dict):
            return {k: convert_to_nested_dict(v) for k, v in obj.items()}

        # Handle TelescopeSettings objects
        if isinstance(
            obj, (ATCATelescopeSettings, MWATelescopeSettings, BaseTelescopeSettings)
        ):
            settings_dict = {}
            for key, value in obj.__dict__.items():
                if key.startswith('_'):  # Skip private attributes
                    continue
                settings_dict[key] = convert_to_nested_dict(value)
            return settings_dict

        # Handle objects with __dict__ attribute (custom classes)
        if hasattr(obj, '__dict__'):
            # Get class name for type information
            class_name = obj.__class__.__name__
            attributes = {}

            for key, value in obj.__dict__.items():
                if key.startswith('_'):  # Skip private attributes
                    continue

                # Handle special cases for known types
                if class_name == 'ProposalSettings' or class_name.startswith(
                    'Proposal'
                ):
                    attributes.update(
                        {
                            'id': getattr(obj, 'id', None),
                            'streams': getattr(obj, 'streams', []),
                            'version': getattr(obj, 'version', None),
                            'project_id': convert_to_nested_dict(
                                getattr(obj, 'project_id', None)
                            ),
                            'event_telescope': convert_to_nested_dict(
                                getattr(obj, 'event_telescope', None)
                            ),
                            'proposal_id': getattr(obj, 'proposal_id', None),
                            'proposal_description': getattr(
                                obj, 'proposal_description', None
                            ),
                            'priority': getattr(obj, 'priority', None),
                            'testing': str(getattr(obj, 'testing', None)),
                            'source_type': str(getattr(obj, 'source_type', None)),
                            'telescope_settings': convert_to_nested_dict(
                                getattr(obj, 'telescope_settings', None)
                            ),
                        }
                    )
                elif class_name == 'SkyCoord':
                    return {
                        'ra': getattr(obj, 'ra').deg if hasattr(obj, 'ra') else None,
                        'dec': getattr(obj, 'dec').deg if hasattr(obj, 'dec') else None,
                    }
                else:
                    attributes[key] = convert_to_nested_dict(value)

            return attributes

        # Handle basic types
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()

        # Default: convert to string if can't handle otherwise
        return str(obj)

    except Exception as e:
        print(f"Error converting object to dict: {str(e)}")
        return str(obj)


def log_context(prefix: str = ""):
    """
    Enhanced decorator that logs context with proper nested JSON structure.

    Args:
        prefix (str): Optional prefix for the log filename
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get context from args or kwargs
            context = None
            if len(args) > 1:  # First arg is self, second is context
                context = args[1]
            elif 'context' in kwargs:
                context = kwargs['context']

            if context:
                # Create logs directory
                project_root = get_project_root()
                data_dir = project_root / "data" / "context_logs"
                data_dir.mkdir(parents=True, exist_ok=True)

                # Create filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # Get event ID if available
                event_id = None
                if hasattr(context, 'event'):
                    event_id = getattr(context.event, 'id', None)

                # Create filename
                filename = (
                    f"{prefix}_context_{event_id}_{timestamp}.json"
                    if event_id
                    else f"{prefix}_context_{timestamp}.json"
                )
                filepath = data_dir / filename

                try:
                    # Convert context to nested dictionary
                    context_dict = convert_to_nested_dict(context)

                    # Save to JSON file
                    with open(filepath, 'w') as f:
                        json.dump(context_dict, f, indent=2, default=str)
                    print(f"Context saved to: {filepath}")

                except Exception as e:
                    print(f"Error saving context: {str(e)}")

            # Call the original function
            return func(*args, **kwargs)

        return wrapper

    return decorator
