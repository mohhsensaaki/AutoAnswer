from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from functools import wraps
from typing import Callable
import json
import traceback
import sys


# Decorator to handle response formatting
def response_formatter(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_at = datetime.now()
        try:
            # Call the function and get the response data (should be a dictionary)
            result = await func(*args, **kwargs)
            status_code = result.status_code
            json_str = result.body.decode('utf-8')
            data = json.loads(json_str)
            exception = None
            status = True
        except HTTPException as http_exc:
            # Handle HTTPException specifically
            status_code = http_exc.status_code
            data = {
                'detail': http_exc.detail,
                'headers': http_exc.headers if http_exc.headers else None,
            }
            exception = str(http_exc)
            status = False
        except Exception as e:
            # Handle general exceptions
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_details = traceback.extract_tb(exc_tb)[-1]  # Get the last traceback entry
            line_number = tb_details.lineno
            file_name = tb_details.filename
            status_code = 500
            data = {
                'error': str(e),
                'file': file_name,
                'line': line_number
            }
            exception = f"{exc_type.__name__}: {e} at line {line_number} in {file_name}"
            status = False

        end_at = datetime.now()

        # Prepare the meta data
        meta = {
            'start_at': start_at.isoformat(),
            'end_at': end_at.isoformat(),
            'run_time_duration': (end_at - start_at).seconds,
            'exception': exception
        }

        # Prepare the final response structure
        response_data = {
            'status': status,
            'meta': meta,
            'data': data  # Method response data
        }

        # Return the JSONResponse with the correct structure
        return JSONResponse(content=response_data, status_code=status_code)

    return wrapper
