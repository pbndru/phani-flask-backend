from prisma import Prisma

async def get_request_type_id(db: Prisma, request_type: str):
    """Returns the DB id of a request type"""
    req_type = await db.requesttype.find_first(where={"name": request_type})
    return req_type.id

async def get_data_source_id(db: Prisma, data_source: str):
    """Returns the DB id of a data source"""
    data_source_db = await db.datasource.find_first(where={"name": data_source})
    return data_source_db.id

async def get_feedback_options_ids(db: Prisma, feedback_types: list):
    """Returns the DB ids of feedback options"""
    ids_found = []
    for ft in feedback_types:
        ft_found = await db.feedbackoptions.find_first(where={"name": ft})
        ids_found.append(ft_found.id)
    return ids_found

async def get_message_types(db: Prisma):
    """Returns the DB IDs of the message types"""
    message_types = await db.messagetype.find_many()
    error_type_id = next(
        (type for type in message_types if type.name == "Error"), None
    ).id
    non_error_type_id = next(
        (type for type in message_types if type.name == "Non-error"), None
    ).id
    return non_error_type_id, error_type_id

async def create_or_retrieve_user(
    db: Prisma, 
    hashed_email: str, 
    encrypted_email: str,
):
    """Determines whether a user is existing or new in the DB"""
    user_record = await db.users.find_unique(where={"unique_identifier": hashed_email})
    if user_record is None:
        user_record = await db.users.create(
            data={
                "unique_identifier": hashed_email,
                "email": encrypted_email,
            }
        )
    return user_record

def parse_response(response: any):
    """Handling for different types of responses"""
    if isinstance(response, list):
        joined_response = ", ".join(response)
        return joined_response
    elif isinstance(response, str):
        return response

def transform_citations(citations: any, message_id: int):
    """Transforms array of citations to match database schema"""
    return [
        {
            "message_id": message_id,
            "title": ct["title"],
            "url": ct.get("source", ""),
            "source_extracts": ct.get("content", ""),
        }
        for ct in citations
    ]

async def handle_request(
    request: any,
    chat_history: any,
    query: str,
    response: str,
    citations: any,
    request_type: str,
):
    """Decodes token and posts to the database"""
    from db.post_query import post_query
    from db.utils.decode_token import decode_token

    access_token = request.headers.get("x-access-token", None)
    session_id = request.headers.get("session-id", "default-session")
    
    hashed_email, encrypted_email, *_ = await decode_token(access_token)
    
    message_id = await post_query(
        query,
        chat_history,
        hashed_email,
        encrypted_email,
        response,
        citations,
        request_type,
        session_id,
    )
    
    if isinstance(message_id, int):
        return message_id
    else:
        raise RuntimeError("Error whilst posting to database")
