from fastapi import HTTPException, status

def validate_search_query(query: str | None):
    if query and len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter more than one character."
        )
