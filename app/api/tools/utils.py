import concurrent.futures
import json
import base64
import os

def run_function_in_parallel(func, args_list):
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()  # Get the result or handle exceptions here
                # print(f"Function {func.__name__} with args {args} completed with result: {result}")
            except Exception as e:
                print(f"Function {func.__name__} failed: {e}")

# to encode vars use encoded_json = base64.b64encode(json.dumps(creds_json).encode('utf-8')).decode('utf-8')
def encoded_var_to_creds(env_var_name):
    """
    Decodes an environment variable containing Base64 encoded JSON,
    checks for existing file, and returns the path if found.

    Args:
        env_var_name (str): Name of the environment variable.

    Returns:
        str: Path to the JSON file (if exists) or None.
    """
    encoded_json = os.getenv(env_var_name)
    if not encoded_json:
        return None  # Environment variable not found

    filename = env_var_name + '.json'
    if os.path.isfile(filename):
        return filename  # File exists, return the path

    decoded_json = json.loads(base64.b64decode(encoded_json).decode('utf-8'))
    with open(filename, "w") as json_file:
        json.dump(decoded_json, json_file, indent=4)
    return filename
