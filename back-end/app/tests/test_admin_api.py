from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from app.api.admin import AdminViewSet
from app.models import OcservUser
from app.tests import (
    OcservTestAbstract,
    default_configs,
    admin_username,
    admin_password,
    update_default_configs,
)


class AdminApiTest(OcservTestAbstract):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def setUp(self) -> None:
        admin, _ = User.objects.get_or_create(
            username=admin_username,
            defaults={"password": make_password(admin_password), "is_superuser": True},
        )
        self.token, _ = Token.objects.get_or_create(user=admin)

    def test_create_admin_config(self):
        data = {
            "username": "test_admin_fake",
            "password": "test_admin_passwd_fake",
            **default_configs,
        }
        request = self.factory.post("/admin/create/", data=data)
        response = AdminViewSet.as_view({"post": "create_admin_configs"})(request)
        if response.status_code != 400:
            self.check_status_and_errors(response, 201)
            self.assertEqual(response.data["user"]["username"], "test_admin")
        else:
            self.check_status_and_errors(response, 400, "Admin config exists!")

    def test_login(self):
        token = self.login(
            username="test_admin_fake", password="test_admin_passwd_fake", status=400
        )
        if not token:
            self.login(status=200)

    def test_logout(self):
        request = self.factory.delete("/admin/logout/", headers=self.get_header)
        response = AdminViewSet.as_view({"delete": "logout"})(request)
        self.check_status_and_errors(response, 204)

    def test_configuration_get(self):
        request = self.factory.get("/admin/configuration/", headers=self.get_header)
        response = AdminViewSet.as_view({"get": "configuration"})(request)
        self.check_status_and_errors(response, 200)
        self.assertIn("default_configs", response.data)
        self.assertIn("captcha_secret_key", response.data)
        self.assertEqual(response.data["default_configs"]["ipv4-network"], "172.16.12.1/22")
        self.assertEqual(response.data["default_traffic"], 10)

    @patch("ocserv.modules.handlers.OcservGroupHandler.update_defaults")
    def test_configuration_update(self, *args, **kwargs):
        request = self.factory.patch(
            "/admin/configuration/", headers=self.get_header, data=update_default_configs
        )
        response = AdminViewSet.as_view({"patch": "configuration"})(request)
        self.check_status_and_errors(response, 202)
        self.assertEqual(response.data["default_configs"]["mtu"], 1500)

    @patch("ocserv.modules.handlers.OcctlHandler.show")
    @patch("ocserv.modules.handlers.OcservUserHandler.online")
    def test_dashboard(self, mock_data_online, mock_data_show):
        mock_data_online.return_value = []
        mock_data_show.return_value = {
            "show_ip_bans": [],
            "show_status": "Note: the printed statistics are not real-time; session time\n"
            "as well as RX and TX data are updated on user disconnect\n\nGeneral info:"
            "\n\tStatus: online\n\tServer PID: 22\n\tSec-mod PID: 26\n\t"
            "Up since: 2024-04-14 12:02 (   28s)\n\tActive sessions: 0\n\t"
            "Total sessions: 0\n\tTotal authentication failures: 0\n\t"
            "IPs in ban list: 0\n\nCurrent stats period:\n\t"
            "Last stats reset: 2024-04-14 12:02 (   28s)\n\t"
            "Sessions handled: 0\n\tTimed out sessions: 0\n\t"
            "Timed out (idle) sessions: 0\n\tClosed due to error sessions: 0\n\t"
            "Authentication failures: 0\n\tAverage auth time:     0s\n\t"
            "Max auth time:     0s\n\tAverage session time:     0s\n\t"
            "Max session time:     0s\n\tRX: 0 bytes\n\tTX: 0 bytes\n",
            "show_iroutes": {},
        }
        request = self.factory.get("/admin/dashboard/", headers=self.get_header)
        response = AdminViewSet.as_view({"get": "dashboard"})(request)
        self.check_status_and_errors(response, 200)
        self.assertIn("Note", response.data["show_status"], "Note is not present in show_status")
        self.assertEqual(response.data["show_ip_bans"], [])
        self.assertEqual(response.data["show_iroutes"], {})

    def test_change_password(self):
        staff_username = "test_staff"
        staff_password = "test_staff_password"
        user = User.objects.create_user(
            username=staff_username,
            password=staff_password,
            is_staff=False,
            is_superuser=False,
        )
        self.token = self.login(staff_username, staff_password)
        data = {
            "old_password": staff_password,
            "password": "new_test_staff_password",
        }
        request = self.factory.post("/admin/change_password/", headers=self.get_header, data=data)
        response = AdminViewSet.as_view({"post": "change_password"})(request)
        self.check_status_and_errors(response, 202)
        self.token = None
        user.delete()

    def test_staff_list(self):
        request = self.factory.get("/admin/staffs/", headers=self.get_header)
        response = AdminViewSet.as_view({"get": "staffs"})(request)
        self.check_status_and_errors(response, 200)
        self.assertIsInstance(response.data, list)

    def test_staff_create(self):
        data = {"username": "setup_test_staff1", "password": "setup_test_staff_passwd"}
        request = self.factory.post("/admin/staffs/", headers=self.get_header, data=data)
        response = AdminViewSet.as_view({"post": "staffs"})(request)
        self.check_status_and_errors(response, 202)
        self.assertEqual(response.data.get("username"), "setup_test_staff1")

        # recreate same user
        request = self.factory.post("/admin/staffs/", headers=self.get_header, data=data)
        response = AdminViewSet.as_view({"post": "staffs"})(request)
        self.check_status_and_errors(response, 200)
        self.assertEqual(response.data.get("username"), "setup_test_staff1")

    def test_staff_delete(self):
        headers = self.get_header
        request = self.factory.delete("/admin/staffs/3/", headers=headers)
        response = AdminViewSet.as_view({"delete": "delete_staff"})(request, pk=3)
        self.check_status_and_errors(response, 204)

        request = self.factory.delete("/admin/staffs/30/", headers=headers)
        response = AdminViewSet.as_view({"delete": "delete_staff"})(request, pk=30)
        self.check_status_and_errors(response, 404, "Staff not found!")
