from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from utils.crypto import decrypt_data, encrypt_data
from utils.s3 import get_s3_client
from fastapi import UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uuid
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}

class Payload(BaseModel):
    payload: str


class SessionRequest(BaseModel):
    session_id: str


class ObjectRequest(BaseModel):
    session_id: str
    bucket: str
    prefix: str = ""

@app.post("/connect")
def connect(data: Payload):

    try:

        # Decrypt incoming payload
        decrypted = decrypt_data(
            data.payload
        )

        access_key = decrypted["access_key"]
        secret_key = decrypted["secret_key"]
        region = decrypted["region"]
        

        # Create S3 client
        s3 = get_s3_client(
            access_key,
            secret_key,
            region
        )

        # Validate credentials
        s3.list_buckets()

        # Generate session ID
        session_id = str(
            uuid.uuid4()
        )

        sessions[session_id] = {

            "access_key": access_key,

            "secret_key": secret_key,

            "region": region,

            "created_at":
                datetime.utcnow(),

            "expires_at":
                datetime.utcnow()
                + timedelta(hours=1)
        }

        encrypted_response = encrypt_data({
            "message": "Connected Successfully",
            "session_id": session_id
        })

        return {
            "payload": encrypted_response
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@app.post("/buckets")
def buckets(data: Payload):

    try:

        decrypted = decrypt_data(
            data.payload
        )

        session_id = decrypted["session_id"]

        # Validate session
        if session_id not in sessions:

            raise HTTPException(
                status_code=401,
                detail="Invalid session"
            )

        session = sessions[
            session_id
        ]

        # Create S3 client
        s3 = get_s3_client(
            session["access_key"],
            session["secret_key"],
            session["region"]
        )

        # Fetch buckets
        response = s3.list_buckets()

        bucket_list = []

        for bucket in response["Buckets"]:

            bucket_list.append(
                bucket["Name"]
            )
        
        encrypted_response = encrypt_data({
            "buckets": bucket_list
        })

        return {
            "payload": encrypted_response
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@app.post("/objects")
def objects(data: Payload):

    try:

        decrypted = decrypt_data(
            data.payload
        )

        session_id = decrypted["session_id"]

        bucket = decrypted["bucket"]

        prefix = decrypted.get(
            "prefix",
            ""
        )

        if session_id not in sessions:

            raise HTTPException(
                status_code=401,
                detail="Invalid session"
            )

        session = sessions[
            session_id
        ]

        s3 = get_s3_client(
            session["access_key"],
            session["secret_key"],
            session["region"]
        )

        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter="/"
        )

        folders = []
        files = []

        for folder in response.get(
            "CommonPrefixes",
            []
        ):

            folders.append(
                folder["Prefix"]
            )

        for file in response.get(
            "Contents",
            []
        ):

            key = file["Key"]

            if key == prefix:
                continue

            files.append({
                "name": key,
                "size": file["Size"],
                "last_modified": str(
                    file["LastModified"]
                ),

                "storage_class": file.get(
                    "StorageClass",
                    "STANDARD"
                ),

                "etag": file.get(
                    "ETag",
                    ""
                )
            })

        encrypted_response = encrypt_data({

            "current_path": prefix,

            "folders": folders,

            "files": files
        })

        return {
            "payload": encrypted_response
        }

    except HTTPException as e:
        raise e

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@app.post("/upload")
async def upload_file(

    session_id: str = Form(...),
    bucket: str = Form(...),
    prefix: str = Form(""),

    file: UploadFile = File(...)
):

    try:

        # Validate session
        if session_id not in sessions:

            raise HTTPException(
                status_code=401,
                detail="Invalid session"
            )

        session = sessions[
            session_id
        ]

        # Create S3 client
        s3 = get_s3_client(
            session["access_key"],
            session["secret_key"],
            session["region"]
        )

        # Final S3 path
        s3_key = f"{prefix}{file.filename}"

        # Read uploaded file
        contents = await file.read()

        # Upload to S3
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=contents
        )

        encrypted_response = encrypt_data({
            "message": "File uploaded successfully",
            "key": s3_key
        })

        return {
            "payload": encrypted_response
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
@app.post("/validate-session")
def validate_session(
    data: Payload
):

    decrypted = decrypt_data(
        data.payload
    )

    session_id = decrypted["session_id"]

    if session_id not in sessions:

        raise HTTPException(
            status_code=401,
            detail="Invalid session"
        )

    session = sessions[
        session_id
    ]

    if (
        session["expires_at"]
        < datetime.utcnow()
    ):

        del sessions[
            session_id
        ]

        raise HTTPException(
            status_code=401,
            detail="Session expired"
        )

    encrypted_response = encrypt_data({
        "valid": True
    })

    return {
        "payload": encrypted_response
    }


@app.post("/delete-file")
def delete_file(data: Payload):

    try:

        # =========================
        # DECRYPT PAYLOAD
        # =========================

        decrypted = decrypt_data(
            data.payload
        )

        session_id = decrypted["session_id"]

        bucket = decrypted["bucket"]

        key = decrypted["key"]


        # =========================
        # VALIDATE SESSION
        # =========================

        if session_id not in sessions:

            raise HTTPException(
                status_code=401,
                detail="Invalid session"
            )


        session = sessions[
            session_id
        ]


        # =========================
        # CREATE S3 CLIENT
        # =========================

        s3 = get_s3_client(
            session["access_key"],
            session["secret_key"],
            session["region"]
        )


        # =========================
        # DELETE FILE
        # =========================

        s3.delete_object(
            Bucket=bucket,
            Key=key
        )


        # =========================
        # ENCRYPT RESPONSE
        # =========================

        encrypted_response = encrypt_data({

            "message":
                "File deleted successfully",

            "deleted_key":
                key
        })


        return {
            "payload":
                encrypted_response
        }


    except HTTPException as e:

        raise e


    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@app.get("/health")
def health():

    return {
        "status": "ok"
    }