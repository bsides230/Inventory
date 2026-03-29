from pathlib import Path

import pytest

from services.recipients import RecipientConfigError, RecipientConfigStore, parse_recipients_file


def test_parse_recipients_file_accepts_comments_and_dedupes(tmp_path):
    path = tmp_path / "order_recipients.txt"
    path.write_text("# comment\nOPS@EXAMPLE.com\n\nops@example.com\nteam@example.com\n")

    recipients = parse_recipients_file(path)

    assert recipients == ["ops@example.com", "team@example.com"]


def test_parse_recipients_file_rejects_invalid_line(tmp_path):
    path = tmp_path / "order_recipients.txt"
    path.write_text("good@example.com\nnot-an-email\n")

    with pytest.raises(RecipientConfigError):
        parse_recipients_file(path)


def test_recipient_store_reloads_when_file_changes(tmp_path):
    path = tmp_path / "order_recipients.txt"
    path.write_text("alpha@example.com\n")
    store = RecipientConfigStore(path)
    assert store.get_recipients() == ["alpha@example.com"]

    import time
    time.sleep(0.01) # fast tests can write files within the same nanosecond causing signature to not update.
    path.write_text("bravo@example.com\n")
    assert store.get_recipients() == ["bravo@example.com"]
