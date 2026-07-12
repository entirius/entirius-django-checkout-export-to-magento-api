# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


class OrderIdType:
    PRIMARY_KEY = 1
    ORDER_ID = 2
    ORDER_PRETTY_ID = 3

    @staticmethod
    def get_type_name_and_slug(id: int) -> (str, str):
        if OrderIdType.PRIMARY_KEY == id:
            return "Primary Key", "primary_key"
        elif OrderIdType.ORDER_ID == id:
            return "Order ID", "order_id"
        elif OrderIdType.ORDER_PRETTY_ID == id:
            return "Order Pretty ID", "order_pretty_id"
        else:
            raise ValueError(f"Wrong ID: {id}")

    @staticmethod
    def get_type_name(id: int) -> str:
        name, slug = OrderIdType.get_type_name_and_slug(id)
        return name

    @staticmethod
    def get_type_slug(id: int) -> str:
        name, slug = OrderIdType.get_type_name_and_slug(id)
        return slug
