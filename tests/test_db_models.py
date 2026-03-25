import os

from alembic import command
from alembic.config import Config

from db.database import create_session_factory
from db.repositories import OrderDraftRepository, OrderRepository, UserRepository


def test_draft_and_order_crud_flow(tmp_path):
    db_path = tmp_path / "crud_flow.db"
    db_url = f"sqlite:///{db_path}"
    cfg = Config("alembic.ini")

    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url
    try:
        command.upgrade(cfg, "head")

        session_factory = create_session_factory(db_url)
        with session_factory() as session:
            users = UserRepository(session)
            drafts = OrderDraftRepository(session)
            orders = OrderRepository(session)

            user = users.create(external_id="user-1", email="user1@example.com", display_name="User One")
            draft = drafts.create(user_id=user.id, is_rush=True, needed_by="9AM")
            drafts.add_or_update_item(
                draft_id=draft.id,
                item_id="tomatoes",
                category_id="produce",
                item_name="Tomatoes",
                quantity=4,
                unit="case",
            )
            drafts.add_or_update_item(
                draft_id=draft.id,
                item_id="tomatoes",
                category_id="produce",
                item_name="Tomatoes",
                quantity=6,
                unit="case",
            )

            hydrated_draft = drafts.get_with_items(draft.id)
            assert hydrated_draft is not None
            assert len(hydrated_draft.items) == 1
            assert hydrated_draft.items[0].quantity == 6

            order = orders.create_from_draft(hydrated_draft, export_filename="order.xlsx")
            session.commit()

            hydrated_order = orders.get_with_items(order.id)
            assert hydrated_order is not None
            assert hydrated_order.user_id == user.id
            assert hydrated_order.export_filename == "order.xlsx"
            assert len(hydrated_order.items) == 1
            assert hydrated_order.items[0].item_id == "tomatoes"
            assert hydrated_order.items[0].quantity == 6

            submitted_draft = drafts.get_with_items(draft.id)
            assert submitted_draft is not None
            assert submitted_draft.status == "submitted"
    finally:
        if original_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_db_url
