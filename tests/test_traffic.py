# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from uuid import UUID
from unittest.mock import patch
import server
class Inventory(unittest.TestCase):
    def test_search_traffic_register(self):
        i=UUID(int=2);row={"name":"Example","group":"work","uuid":str(i),"traffic_limit":500}
        with patch.object(server,"komari_list_servers",return_value=[row]):self.assertEqual(server.komari_search_servers("example work"),[row])
        with patch.object(server,"access_key",return_value="fixture"),patch.object(server,"komari_get_server",return_value=row),patch.object(server,"komari_latest_status",return_value={"net_total_up":8,"net_total_down":4}),patch.object(server,"api",return_value={"uuid":str(i),"token":"fixture"}):
            self.assertEqual(server.komari_traffic(i)["uploaded_bytes"],8)
            value=server.komari_add_host("Example");self.assertTrue(value["verified"]);self.assertNotIn("token",value)
