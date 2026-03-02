from app.core.domain.item import ItemType
a = ItemType.CONSUMABLE
print(f"a == 'consumable': {a == 'consumable'}")
print(f"str(a): {str(a)}")
b = str(a)
print(f"b == 'consumable': {b == 'consumable'}")
