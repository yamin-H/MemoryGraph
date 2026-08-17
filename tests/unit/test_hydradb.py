"""Unit tests for the HydraDB module."""

import pytest
from unittest.mock import MagicMock, patch


class TestHydraDB:
    """Tests for HydraDB connection and operations."""

    def test_init_with_defaults(self):
        """Test HydraDB initialization with default parameters."""
        from apps.api.db.hydra import HydraDB

        db = HydraDB()

        assert db.uri == "neo4j://127.0.0.1:7687"
        assert db.auth_token == "local-development-token-32-bytes"
        assert db._driver is None

    def test_init_with_custom_params(self):
        """Test HydraDB initialization with custom parameters."""
        from apps.api.db.hydra import HydraDB

        db = HydraDB(uri="neo4j://custom:7687", auth_token="custom-token")

        assert db.uri == "neo4j://custom:7687"
        assert db.auth_token == "custom-token"

    def test_engine_info(self):
        """Test engine metadata identifies HydraDB OSS."""
        from apps.api.db.hydra import HydraDB

        info = HydraDB.engine_info()
        assert info["engine"] == "HydraDB OSS"
        assert "hydra-db/hydradb" in info["image"]

    def test_build_bolt_auth_token_form(self):
        """Test token auth uses neo4j username with HydraDB token password."""
        from apps.api.db.hydra import build_bolt_auth

        auth, username = build_bolt_auth("local-development-token-32-bytes")
        assert username == "neo4j"
        assert auth is not None

        from apps.api.db.hydra import HydraDB

        with patch("apps.api.db.hydra.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance

            db = HydraDB()
            db.connect()

            mock_driver.assert_called_once()
            assert db._driver == mock_instance

    def test_close_closes_driver(self):
        """Test close properly closes driver."""
        from apps.api.db.hydra import HydraDB

        with patch("apps.api.db.hydra.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance

            db = HydraDB()
            db.connect()
            db.close()

            mock_instance.close.assert_called_once()
            assert db._driver is None

    def test_close_idempotent(self):
        """Test close can be called multiple times safely."""
        from apps.api.db.hydra import HydraDB

        with patch("apps.api.db.hydra.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance

            db = HydraDB()
            db.connect()
            db.close()
            db.close()  # Second call should not error

            # close should only be called once since _driver is None after first
            assert mock_instance.close.call_count == 1

    def test_write_fact_creates_nodes(self):
        """Test write_fact creates Fact and Anchor nodes."""
        from apps.api.db.hydra import HydraDB

        with patch("apps.api.db.hydra.GraphDatabase.driver") as mock_driver:
            mock_session = MagicMock()
            mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

            db = HydraDB()
            db.connect()
            db.write_fact(1, "Test fact content")

            mock_session.run.assert_called_once()
            call_args = mock_session.run.call_args
            assert "MERGE (f:Fact" in call_args[0][0]
            assert call_args[1]["id"] == 1
            assert call_args[1]["content"] == "Test fact content"
            assert call_args[1]["anchor_id"] == 1000001

    def test_read_fact_returns_data(self):
        """Test read_fact returns fact data when found."""
        from apps.api.db.hydra import HydraDB

        with patch("apps.api.db.hydra.GraphDatabase.driver") as mock_driver:
            mock_session = MagicMock()
            mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

            mock_record = MagicMock()
            mock_record.__getitem__ = lambda self, key: {"f.id": 1, "f.content": "Test fact"}[key]
            mock_result = MagicMock()
            mock_result.single.return_value = mock_record
            mock_session.run.return_value = mock_result

            db = HydraDB()
            db.connect()
            fact = db.read_fact(1)

            assert fact is not None
            assert fact["id"] == 1
            assert fact["content"] == "Test fact"

    def test_read_fact_returns_none_when_not_found(self):
        """Test read_fact returns None when fact not found."""
        from apps.api.db.hydra import HydraDB

        with patch("apps.api.db.hydra.GraphDatabase.driver") as mock_driver:
            mock_session = MagicMock()
            mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.single.return_value = None
            mock_session.run.return_value = mock_result

            db = HydraDB()
            db.connect()
            fact = db.read_fact(999)

            assert fact is None

    def test_clear_all_deletes_all_nodes(self):
        """Test clear_all deletes all nodes."""
        from apps.api.db.hydra import HydraDB

        with patch("apps.api.db.hydra.GraphDatabase.driver") as mock_driver:
            mock_session = MagicMock()
            mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

            db = HydraDB()
            db.connect()
            db.clear_all()

            mock_session.run.assert_called_once()
            call_args = mock_session.run.call_args
            assert "MATCH (n) DELETE n" in call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])