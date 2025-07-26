"""Error handling patterns for all tool functions."""

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from src.utils.access_control import AccessValidator
from src.utils.common import log_error

P = ParamSpec("P")
T = TypeVar("T")


def handle_tool_errors(
    operation_name: str,
) -> Callable[[Callable[P, dict[str, Any]]], Callable[P, dict[str, Any]]]:
    """Decorator for error handling across all tool functions."""

    def decorator(func: Callable[P, dict[str, Any]]) -> Callable[P, dict[str, Any]]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
                log_error(e, operation_name)
                return AccessValidator.create_error_response(
                    f"Error in {operation_name}: {str(e)}"
                )
            except Exception as e:
                # Catch any other unexpected exceptions
                log_error(e, f"{operation_name}_unexpected")
                return AccessValidator.create_error_response(
                    f"Unexpected error in {operation_name}: {str(e)}"
                )

        return wrapper

    return decorator


def handle_database_errors(
    operation_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for database-specific error handling."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                log_error(e, f"database_{operation_name}")
                return None
            except OSError as e:
                log_error(e, f"database_io_{operation_name}")
                return None
            except Exception as e:
                log_error(e, f"database_unexpected_{operation_name}")
                return None

        return wrapper

    return decorator


def handle_file_operation_errors(
    operation_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for file operation error handling."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except (OSError, FileNotFoundError, PermissionError) as e:
                log_error(e, f"file_{operation_name}")
                return None
            except (ValueError, TypeError) as e:
                log_error(e, f"file_validation_{operation_name}")
                return None
            except Exception as e:
                log_error(e, f"file_unexpected_{operation_name}")
                return None

        return wrapper

    return decorator


def handle_validation_errors(
    operation_name: str, default_value: Any = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for validation error handling with configurable defaults."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                log_error(e, f"validation_{operation_name}")
                return default_value
            except Exception as e:
                log_error(e, f"validation_unexpected_{operation_name}")
                return default_value

        return wrapper

    return decorator


class ErrorHandler:
    """Context manager for error handling in complex operations."""

    def __init__(self, operation_name: str, return_on_error: Any = None):
        self.operation_name = operation_name
        self.return_on_error = return_on_error
        self.error_occurred = False
        self.caught_error: BaseException | None = None

    def __enter__(self) -> "ErrorHandler":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        if exc_type is not None and exc_val is not None:
            self.error_occurred = True
            self.caught_error = exc_val

            if issubclass(
                exc_type, ValueError | TypeError | KeyError | AttributeError | OSError
            ):
                # exc_val is guaranteed to be an Exception subclass here
                if isinstance(exc_val, Exception):
                    log_error(exc_val, self.operation_name)
                return True  # Suppress the exception
            else:
                if isinstance(exc_val, Exception):
                    log_error(exc_val, f"{self.operation_name}_unexpected")
                return True  # Suppress the exception

        return False

    def get_result(self, success_value: Any) -> Any:
        """Get the appropriate result based on whether an error occurred."""
        return self.return_on_error if self.error_occurred else success_value


def safe_execute(
    operation_name: str, func: Callable[..., Any], *args: Any, **kwargs: Any
) -> tuple[Any, bool]:
    """Safely execute a function and return (result, success_flag)."""
    try:
        result = func(*args, **kwargs)
        return result, True
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, operation_name)
        return None, False
    except Exception as e:
        log_error(e, f"{operation_name}_unexpected")
        return None, False


def create_error_response_with_details(
    operation_name: str, error: Exception, include_details: bool = False
) -> dict[str, Any]:
    """Create detailed error response for debugging purposes."""
    log_error(error, operation_name)

    base_response = AccessValidator.create_error_response(
        f"Error in {operation_name}: {str(error)}"
    )

    if include_details:
        base_response["error_details"] = {
            "operation": operation_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

    return base_response
