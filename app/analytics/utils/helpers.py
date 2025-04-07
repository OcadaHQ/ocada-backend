from datetime import datetime
from typing import List, Dict, Any, Optional, Generator

def get_recent_growth_pattern(sequence: List[float]) -> int:
    following_num = None
    meter = 0  # 0: no change, >0: increased this many times, <1: decreased this many times
    for current_num in sequence:
        if following_num is None:
            following_num = current_num
            continue
        
        is_growing = following_num > current_num

        if is_growing and meter >=0:
            meter += 1
            following_num = current_num
        elif not is_growing and meter <=0:
            meter -= 1
            following_num = current_num
        else:
            break
    
    return meter

def get_recent_positive_pattern(sequence: List[float]) -> int:

    meter = 0   # 0: no data/break even, >0: remained positive this many times, <1: remained negative this many times
    for current_num in sequence:
        if type(current_num) is not float:
            continue
        is_profitable = current_num > 0

        if is_profitable and meter >=0:
            meter += 1
        elif not is_profitable and meter <=0:
            meter -= 1
        else:
            break
    
    return meter

def rfc3339_to_datetime(raw_date: str) -> datetime:
    date_format = '%Y-%m-%dT%H:%M:%S%z'
    return datetime.strptime(raw_date, date_format)

def chunk_list(lst: List[Any], chunk_size: int) -> Generator[List[Any], None, None]:
    """Yield successive chunks from lst of size chunk_size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def get_dict_by_id(data: List[Dict[str, Any]], target_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a dictionary from a list by its ID."""
    for item in data:
        if item["id"] == target_id:
            return item
    return None  # Return None if no dictionary with the target_id is found
