import pytest
from unittest.mock import patch, MagicMock
from db import get_db, init_db


def test_init_db_creates_admin_when_users_empty():
    mock_db = MagicMock()
    mock_db.users.count_documents.return_value = 0
    mock_db.users.insert_one = MagicMock()

    with patch('db.get_db', return_value=mock_db):
        init_db()

    mock_db.users.insert_one.assert_called_once()
    call_args = mock_db.users.insert_one.call_args[0][0]
    assert call_args['username'] == 'admin'
    assert call_args['role'] == 'admin'
    assert call_args['must_change_password'] is True


def test_init_db_skips_when_users_exist():
    mock_db = MagicMock()
    mock_db.users.count_documents.return_value = 1

    with patch('db.get_db', return_value=mock_db):
        init_db()

    mock_db.users.insert_one.assert_not_called()
