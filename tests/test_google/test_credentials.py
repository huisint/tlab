# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
from unittest import TestCase, mock

from tlab.google import credentials


CREDENTIALS_MOCK = mock.Mock(spec_set=credentials.Credentials)


@mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config")
class TestCredentials_new(TestCase):

    def test_client_id(self, from_client_config_mock: mock.Mock) -> None:
        flow_mock = from_client_config_mock.return_value
        assert isinstance(flow_mock, mock.Mock)
        client_ids = [f"clientId{i}" for i in range(3)]
        for client_id in client_ids:
            from_client_config_mock.reset_mock()
            client_config = credentials.CLIENT_CONFIG.copy()
            client_config["installed"]["client_id"] = client_id
            with self.subTest(client_id=client_id):
                creds = credentials.Credentials.new(client_id=client_id)
                self.assertEqual(creds._credentials, flow_mock.run_local_server.return_value)
                from_client_config_mock.assert_called_once_with(client_config, credentials.SCOPES)

    def test_client_secret(self, from_client_config_mock: mock.Mock) -> None:
        flow_mock = from_client_config_mock.return_value
        assert isinstance(flow_mock, mock.Mock)
        client_secrets = [f"clientSecret{i}" for i in range(3)]
        for client_secret in client_secrets:
            from_client_config_mock.reset_mock()
            client_config = credentials.CLIENT_CONFIG.copy()
            client_config["installed"]["client_secret"] = client_secret
            with self.subTest(client_secret=client_secret):
                creds = credentials.Credentials.new(client_secret=client_secret)
                self.assertEqual(creds._credentials, flow_mock.run_local_server.return_value)
                from_client_config_mock.assert_called_once_with(client_config, credentials.SCOPES)

    def test_run_local_server(self, from_client_config_mock: mock.Mock) -> None:
        flow_mock = from_client_config_mock.return_value
        assert isinstance(flow_mock, mock.Mock)
        for run_local_server in (True, False):
            with self.subTest(run_local_server=run_local_server):
                from_client_config_mock.reset_mock()
                if run_local_server:
                    creds = credentials.Credentials.new(run_local_server=run_local_server)
                    self.assertEqual(creds._credentials, flow_mock.run_local_server.return_value)
                    flow_mock.run_local_server.assert_called_once_with()
                    flow_mock.run_console.assert_not_called()
                else:
                    creds = credentials.Credentials.new(run_local_server=run_local_server)
                    self.assertEqual(creds._credentials, flow_mock.run_console.return_value)
                    flow_mock.run_local_server.assert_not_called()
                    flow_mock.run_console.assert_called_once_with()


@mock.patch("google.oauth2.credentials.Credentials.from_authorized_user_file")
class TestCredentials_from_file(TestCase):
    filename = "tests/gmail.tlabrc.json"

    def test_credentials_valid(self, from_authorized_user_file_mock: mock.Mock) -> None:
        creds_mock = from_authorized_user_file_mock.return_value
        creds_mock.valid = True
        creds = credentials.Credentials.from_file(self.filename)
        self.assertEqual(creds._credentials, creds_mock)
        from_authorized_user_file_mock.assert_called_once_with(self.filename, credentials.SCOPES)
        CREDENTIALS_MOCK.refresh.assert_not_called()

    def test_credentials_invalid_refreshable(self, from_authorized_user_file_mock: mock.Mock) -> None:
        creds_mock = from_authorized_user_file_mock.return_value
        creds_mock.valid = False
        creds_mock.refresh_token = "refresh_token"
        creds = credentials.Credentials.from_file(self.filename)
        self.assertEqual(creds._credentials, creds_mock)
        from_authorized_user_file_mock.assert_called_once_with(self.filename, credentials.SCOPES)
        creds_mock.refresh.assert_called_once()

    def test_credentials_invalid_unrefreshable(self, from_authorized_user_file_mock: mock.Mock) -> None:
        creds_mock = from_authorized_user_file_mock.return_value
        creds_mock.valid = False
        creds_mock.refresh_token = None
        with self.assertRaises(ValueError):
            credentials.Credentials.from_file(self.filename)
        from_authorized_user_file_mock.assert_called_once_with(self.filename, credentials.SCOPES)
        creds_mock.refresh.assert_not_called()


@mock.patch("builtins.open")
@mock.patch("google.oauth2.credentials.Credentials")
class TestCredentials_save(TestCase):

    def test_filename(
        self,
        creds_mock: mock.Mock,
        open_mock: mock.Mock
    ) -> None:
        creds = credentials.Credentials(creds_mock)
        filenames = [f"tests/test_google/gmail.tlabgrc{i}.json" for i in range(3)]
        json_text = '{"token": "crendentials"}'
        for filename in filenames:
            creds_mock.reset_mock()
            open_mock.reset_mock()
            creds_mock.to_json.return_value = json_text
            with self.subTest(filename=filename):
                creds.save(filename)
                open_mock.assert_called_once_with(filename, "w")
                f_mock = open_mock.return_value.__enter__.return_value
                f_mock.write.assert_called_once_with(json_text)
                creds_mock.to_json.assert_called_once()


@mock.patch("google.auth.transport.requests.Request")
@mock.patch("google.oauth2.credentials.Credentials")
class TestCredentials_refresh(TestCase):

    def test(
        self,
        creds_mock: mock.Mock,
        request_mock: mock.Mock
    ) -> None:
        creds = credentials.Credentials(creds_mock)
        creds.refresh()
        creds_mock.refresh.assert_called_once_with(request_mock.return_value)
