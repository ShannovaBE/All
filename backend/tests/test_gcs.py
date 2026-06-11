import importlib
import unittest
from unittest import mock

try:
    from google.auth.compute_engine import credentials as compute_engine_credentials
except ModuleNotFoundError:  # pragma: no cover - depends on local test env
    compute_engine_credentials = None


if compute_engine_credentials is not None:
    class FakeScopedCredentials(compute_engine_credentials.Credentials):
        last_refreshed_scopes = None

        def __init__(self, scopes=None, default_scopes=None, service_account_email="signer@example.com", **kwargs):
            super().__init__(
                service_account_email=service_account_email,
                scopes=scopes,
                default_scopes=default_scopes,
                **kwargs,
            )

        def refresh(self, request):
            type(self).last_refreshed_scopes = tuple(self._scopes or ())
            self.token = "signed-token"


@unittest.skipIf(compute_engine_credentials is None, "google auth dependency not installed")
class TestGcsSignedUrlScopes(unittest.TestCase):
    def test_signed_url_fallback_refreshes_with_cloud_platform_scope(self):
        with mock.patch("google.cloud.storage.Client", return_value=mock.Mock()):
            gcs = importlib.import_module("gcs")
            gcs = importlib.reload(gcs)

        FakeScopedCredentials.last_refreshed_scopes = None
        creds = FakeScopedCredentials(scopes=("https://www.googleapis.com/auth/devstorage.read_write",))

        kwargs = gcs._signed_url_kwargs(creds)

        self.assertEqual(gcs.SIGNED_URL_SCOPES, FakeScopedCredentials.last_refreshed_scopes)
        self.assertEqual("signer@example.com", kwargs["service_account_email"])
        self.assertEqual("signed-token", kwargs["access_token"])


if __name__ == "__main__":
    unittest.main()
