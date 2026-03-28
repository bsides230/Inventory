from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db.models import Order, OrderDraft, OrderDraftItem, OrderItem, User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, external_id: str, email: str, display_name: str) -> User:
        user = User(external_id=external_id, email=email, display_name=display_name)
        self.session.add(user)
        self.session.flush()
        return user

    def get_by_external_id(self, external_id: str) -> User | None:
        stmt = select(User).where(User.external_id == external_id)
        return self.session.scalar(stmt)


class OrderDraftRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: int, draft_name: str | None = None, is_rush: bool = False, needed_by: str | None = None) -> OrderDraft:
        draft = OrderDraft(user_id=user_id, draft_name=draft_name, is_rush=is_rush, needed_by=needed_by)
        self.session.add(draft)
        self.session.flush()
        return draft

    def get_active_for_user(self, user_id: int, with_items: bool = False) -> OrderDraft | None:
        stmt = select(OrderDraft).where(OrderDraft.user_id == user_id, OrderDraft.status == "active")
        if with_items:
            stmt = stmt.options(selectinload(OrderDraft.items))
        return self.session.scalar(stmt.order_by(OrderDraft.id.desc()))

    def get_all_active_for_user(self, user_id: int) -> list[OrderDraft]:
        stmt = select(OrderDraft).where(OrderDraft.user_id == user_id, OrderDraft.status == "active").order_by(OrderDraft.updated_at.desc())
        return list(self.session.scalars(stmt))

    def get_by_id_for_user(self, draft_id: int, user_id: int, with_items: bool = False) -> OrderDraft | None:
        stmt = select(OrderDraft).where(OrderDraft.id == draft_id, OrderDraft.user_id == user_id)
        if with_items:
            stmt = stmt.options(selectinload(OrderDraft.items))
        return self.session.scalar(stmt)

    def get_or_create_active_for_user(self, user_id: int) -> OrderDraft:
        draft = self.get_active_for_user(user_id)
        if draft is None:
            draft = self.create(user_id=user_id, draft_name="Draft 1")
        return draft

    def add_or_update_item(
        self,
        draft_id: int,
        item_id: str,
        category_id: str,
        item_name: str,
        quantity: int,
        unit: str,
    ) -> OrderDraftItem:
        stmt = select(OrderDraftItem).where(
            OrderDraftItem.draft_id == draft_id,
            OrderDraftItem.item_id == item_id,
        )
        item = self.session.scalar(stmt)
        if item is None:
            item = OrderDraftItem(
                draft_id=draft_id,
                item_id=item_id,
                category_id=category_id,
                item_name=item_name,
                quantity=quantity,
                unit=unit,
            )
            self.session.add(item)
        else:
            item.category_id = category_id
            item.item_name = item_name
            item.quantity = quantity
            item.unit = unit
        self.session.flush()
        return item

    def remove_item(self, draft_id: int, item_id: str) -> None:
        stmt = select(OrderDraftItem).where(OrderDraftItem.draft_id == draft_id, OrderDraftItem.item_id == item_id)
        item = self.session.scalar(stmt)
        if item is not None:
            self.session.delete(item)
            self.session.flush()

    def get_with_items(self, draft_id: int) -> OrderDraft | None:
        stmt = select(OrderDraft).options(selectinload(OrderDraft.items)).where(OrderDraft.id == draft_id)
        return self.session.scalar(stmt)

    def rename(self, draft_id: int, name: str) -> None:
        draft = self.session.get(OrderDraft, draft_id)
        if draft:
            draft.draft_name = name
            self.session.flush()

    def delete(self, draft_id: int, user_id: int) -> bool:
        draft = self.session.scalar(
            select(OrderDraft).where(OrderDraft.id == draft_id, OrderDraft.user_id == user_id)
        )
        if draft:
            self.session.delete(draft)
            self.session.flush()
            return True
        return False

    def count_items(self, draft_id: int) -> int:
        stmt = select(OrderDraftItem).where(OrderDraftItem.draft_id == draft_id)
        return len(list(self.session.scalars(stmt)))


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_from_draft(self, draft: OrderDraft, export_filename: str | None = None, location_pin: str | None = None, location_name: str | None = None) -> Order:
        order = Order(
            user_id=draft.user_id,
            is_rush=draft.is_rush,
            needed_by=draft.needed_by,
            export_filename=export_filename,
            delivery_status="pending",
            delivery_attempts=0,
            location_pin=location_pin,
            location_name=location_name,
        )
        self.session.add(order)
        self.session.flush()

        for draft_item in draft.items:
            self.session.add(
                OrderItem(
                    order_id=order.id,
                    item_id=draft_item.item_id,
                    category_id=draft_item.category_id,
                    item_name=draft_item.item_name,
                    quantity=draft_item.quantity,
                    unit=draft_item.unit,
                )
            )

        draft.status = "submitted"
        self.session.flush()
        return order

    def get_with_items(self, order_id: int) -> Order | None:
        stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        return self.session.scalar(stmt)

    def update_delivery_status(self, order_id: int, status: str, attempts: int, error: str | None = None) -> Order | None:
        order = self.session.get(Order, order_id)
        if order is None:
            return None

        order.delivery_status = status
        order.delivery_attempts = attempts
        order.delivery_error = error
        if status == "sent":
            order.delivered_at = datetime.now(UTC)
        self.session.flush()
        return order
