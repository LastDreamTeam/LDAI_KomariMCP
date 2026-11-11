# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from unittest.mock import patch
from uuid import UUID

import server

class MetadataTest(unittest.TestCase):
    def test_write_readback(self):
        node = UUID(int=1)
        before = {"uuid":str(node),"name":"previous"}
        after = {"uuid":str(node),"name":"example"}
        with patch.object(server,"api",side_effect=[before,{},after]) as api:
            result = server.komari_update_server(node,server.Changes(name="example"))
        self.assertTrue(result["verified"])
        self.assertEqual(api.call_args_list[1].args[1],{"name":"example"})
        self.assertEqual(result["previous"],{"name":"previous"})

    def test_rejects_timezone_ambiguity(self):
        with self.assertRaisesRegex(ValueError,"timezone"):
            server.komari_update_server(UUID(int=1),server.Changes(expired_at="2030-01-01T00:00:00"))

    def test_result_filter(self):
        self.assertEqual(server.public([{"name":"example","api_key":"fixture","token":"fixture"}]),[{"name":"example"}])
