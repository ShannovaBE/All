import os
import datetime

import google.auth.credentials
from google.auth.transport.requests import Request
from google.cloud import storage

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "shannova-datasets-sublime")
SIGNED_URL_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)

try:
    gcs_client = storage.Client()
except Exception as e:
    print(f"Warning: Failed to initialize GCS client: {e}")
    gcs_client = None

def _require_client():
    if gcs_client is None:
        raise RuntimeError("GCS client is not configured")
    return gcs_client


def _signed_url_kwargs(credentials):
    # Cloud Run often provides token-only compute credentials. The storage
    # client can still sign V4 URLs if we pass a fresh access token plus the
    # service account email, which uses IAM signBlob under the hood.
    if isinstance(credentials, google.auth.credentials.Signing):
        return {}

    scoped_credentials = credentials
    if isinstance(credentials, google.auth.credentials.Scoped):
        scoped_credentials = credentials.with_scopes(SIGNED_URL_SCOPES)

    request = Request()
    scoped_credentials.refresh(request)
    service_account_email = getattr(scoped_credentials, "service_account_email", None)
    if not scoped_credentials.token or not service_account_email:
        raise RuntimeError("Credentials cannot sign URLs in this environment")

    return {
        "service_account_email": service_account_email,
        "access_token": scoped_credentials.token,
    }

def put_object(key, body, content_type):
    client = _require_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(key)
    blob.upload_from_string(body, content_type=content_type)

def generate_presigned_url(key, filename=None, mime=None, expires_in=600):
    client = _require_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(key)
    signing_kwargs = _signed_url_kwargs(client._credentials)
    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(seconds=expires_in),
        response_disposition=f'attachment; filename="{filename}"' if filename else None,
        response_type=mime if mime else None,
        **signing_kwargs,
    )

def delete_object(key):
    client = _require_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(key)
    if blob.exists():
        blob.delete()
