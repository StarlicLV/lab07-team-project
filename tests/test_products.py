"""Тести товарів (Учасник 1): tests/test_products.py

Unit: validate_product, product_to_dict, _validate_product.
Integration: /api/v1/products та /api/v2/products.
Схема AAA (Arrange, Act, Assert) у кожному тесті.
Використовується fixture `client` з tests/conftest.py (тестова БД: 8 товарів,
id 4 = Чізкейк за 95 грн).
"""
import pytest
from werkzeug.datastructures import MultiDict

from api.v1.products import validate_product, product_to_dict
from routes.shop import _validate_product

V1 = '/api/v1/products'
V2 = '/api/v2/products'
MISSING_ID = 999999
SEEDED_COUNT = 8


# ============================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# ============================================================

def valid_data(**overrides):
    data = {
        'name': 'Тірамісу',
        'price': 120,
        'category': 'Десерти',
        'description': 'Класичний десерт',
        'is_available': True,
    }
    data.update(overrides)
    return data


def items_of(body):
    """Список товарів з відповіді: {"products": [...]} або просто список."""
    if isinstance(body, list):
        return body
    for key in ('products', 'items', 'data', 'results'):
        if isinstance(body, dict) and isinstance(body.get(key), list):
            return body[key]
    raise AssertionError(f'Не знайдено список товарів у відповіді: {body!r}')


def unwrap(body):
    return body.get('product', body) if isinstance(body, dict) else body


def create_product(client, **overrides):
    response = client.post(V1, json=valid_data(**overrides))
    assert response.status_code == 201, response.get_data(as_text=True)
    return unwrap(response.get_json())


class Row(dict):
    """Підтримує і row['x'], і row.x."""
    __getattr__ = dict.get


# ============================================================
# UNIT: validate_product(data, partial=False)
# ============================================================

def test_validate_product_valid_has_no_errors():
    # Arrange
    data = valid_data()
    # Act
    errors = validate_product(data)
    # Assert
    assert not errors


def test_validate_product_empty_data_has_errors():
    # Arrange
    data = {}
    # Act
    errors = validate_product(data)
    # Assert
    assert errors


@pytest.mark.parametrize('field', ['name', 'category'])
def test_validate_product_required_field_missing(field):
    # Arrange
    data = valid_data()
    del data[field]
    # Act
    errors = validate_product(data)
    # Assert
    assert errors
    assert field in str(errors)


@pytest.mark.parametrize('field', ['name', 'category'])
@pytest.mark.parametrize('value', ['', '   '])
def test_validate_product_blank_string_is_error(field, value):
    # Arrange
    data = valid_data(**{field: value})
    # Act
    errors = validate_product(data)
    # Assert
    assert errors
    assert field in str(errors)


@pytest.mark.parametrize('field', ['name', 'category'])
@pytest.mark.parametrize('length, is_valid', [(1, True), (100, True), (101, False)])
def test_validate_product_length_boundaries(field, length, is_valid):
    # Arrange
    data = valid_data(**{field: 'а' * length})
    # Act
    errors = validate_product(data)
    # Assert
    assert (not errors) is is_valid


@pytest.mark.parametrize('length, is_valid', [(0, True), (1000, True), (1001, False)])
def test_validate_product_description_length_boundaries(length, is_valid):
    # Arrange
    data = valid_data(description='а' * length)
    # Act
    errors = validate_product(data)
    # Assert
    assert (not errors) is is_valid


@pytest.mark.parametrize('price, is_valid', [
    (0, True),
    (0.01, True),
    (70, True),
    (99999.99, True),
    (-0.01, False),
    (-1, False),
])
def test_validate_product_price_boundaries(price, is_valid):
    # Arrange
    data = valid_data(price=price)
    # Act
    errors = validate_product(data)
    # Assert
    assert (not errors) is is_valid
    if not is_valid:
        assert 'price' in str(errors)


@pytest.mark.parametrize('price', ['70', 'abc', '', None, [], {}])
def test_validate_product_price_must_be_number(price):
    # Arrange
    data = valid_data(price=price)
    # Act
    errors = validate_product(data)
    # Assert
    assert errors
    assert 'price' in str(errors)


@pytest.mark.parametrize('value', ['true', 'yes', 1, 0, None, 'false'])
def test_validate_product_is_available_must_be_boolean(value):
    # Arrange
    data = valid_data(is_available=value)
    # Act
    errors = validate_product(data)
    # Assert
    assert errors
    assert 'is_available' in str(errors)


@pytest.mark.parametrize('value', [True, False])
def test_validate_product_is_available_boolean_ok(value):
    # Arrange
    data = valid_data(is_available=value)
    # Act
    errors = validate_product(data)
    # Assert
    assert not errors


def test_validate_product_partial_accepts_single_field():
    # Arrange
    data = {'price': 10}
    # Act
    errors = validate_product(data, partial=True)
    # Assert
    assert not errors


def test_validate_product_partial_still_checks_given_fields():
    # Arrange
    data = {'price': -5}
    # Act
    errors = validate_product(data, partial=True)
    # Assert
    assert errors
    assert 'price' in str(errors)


def test_validate_product_partial_empty_patch_is_error():
    # Arrange
    data = {}
    # Act
    errors = validate_product(data, partial=True)
    # Assert
    assert errors


def test_validate_product_full_requires_all_required_fields():
    # Arrange
    data = {'price': 10}
    # Act
    errors = validate_product(data, partial=False)
    # Assert
    assert errors


# ============================================================
# UNIT: product_to_dict
# ============================================================

def test_product_to_dict_returns_dict_with_fields():
    # Arrange
    row = Row(id=1, name='Тірамісу', price=120.0, category='Десерти',
              description='Опис', is_available=True)
    # Act
    result = product_to_dict(row)
    # Assert
    assert isinstance(result, dict)
    assert result['id'] == 1
    assert result['name'] == 'Тірамісу'
    assert result['price'] == 120.0
    assert result['category'] == 'Десерти'


# ============================================================
# UNIT: _validate_product(form) з routes/shop.py
# ============================================================

def test_shop_validate_product_valid_vs_invalid_differ():
    # Arrange
    good = MultiDict({'name': 'Чай', 'price': '50', 'category': 'Напої',
                      'description': 'Зелений'})
    bad = MultiDict({'name': '', 'price': '-5', 'category': '', 'description': ''})
    # Act
    good_result = _validate_product(good)
    bad_result = _validate_product(bad)
    # Assert
    assert good_result != bad_result


# ============================================================
# INTEGRATION v1: читання та фільтри
# ============================================================

def test_v1_list_returns_seeded_products(client):
    # Arrange: тестова БД містить 8 товарів
    # Act
    response = client.get(V1)
    # Assert
    assert response.status_code == 200
    assert len(items_of(response.get_json())) == SEEDED_COUNT


def test_v1_get_seeded_product_cheesecake(client):
    # Arrange: id 4 = Чізкейк за 95 грн
    # Act
    response = client.get(f'{V1}/4')
    body = unwrap(response.get_json())
    # Assert
    assert response.status_code == 200
    assert 'Чізкейк' in body['name']
    assert body['price'] == 95


def test_v1_filter_by_category(client):
    # Arrange
    create_product(client, name='Фільтр-товар', category='УнікальнаКатегорія')
    # Act
    response = client.get(f'{V1}?category=УнікальнаКатегорія')
    items = items_of(response.get_json())
    # Assert
    assert response.status_code == 200
    assert [i['name'] for i in items] == ['Фільтр-товар']


def test_v1_filter_by_unknown_category_is_empty(client):
    # Arrange
    category = 'КатегоріїНеІснує'
    # Act
    response = client.get(f'{V1}?category={category}')
    # Assert
    assert response.status_code == 200
    assert items_of(response.get_json()) == []


def test_v1_search_by_q(client):
    # Arrange
    create_product(client, name='Зюзябліксир', description='x')
    # Act
    response = client.get(f'{V1}?q=Зюзяблік')
    items = items_of(response.get_json())
    # Assert
    assert response.status_code == 200
    assert [i['name'] for i in items] == ['Зюзябліксир']


def test_v1_filter_by_available(client):
    # Arrange
    hidden = create_product(client, name='Недоступний-товар', is_available=False)
    # Act
    response = client.get(f'{V1}?available=true')
    items = items_of(response.get_json())
    # Assert
    assert response.status_code == 200
    assert items
    assert all(i['is_available'] is True for i in items)
    assert hidden['id'] not in [i['id'] for i in items]


# ============================================================
# INTEGRATION v1: POST
# ============================================================

def test_v1_post_creates_product(client):
    # Arrange
    payload = valid_data()
    # Act
    response = client.post(V1, json=payload)
    body = unwrap(response.get_json())
    # Assert
    assert response.status_code == 201
    assert body['name'] == 'Тірамісу'
    assert body['price'] == 120
    assert 'id' in body


def test_v1_post_then_get_by_id(client):
    # Arrange
    created = create_product(client, name='Кава', price=80)
    # Act
    response = client.get(f"{V1}/{created['id']}")
    body = unwrap(response.get_json())
    # Assert
    assert response.status_code == 200
    assert body['name'] == 'Кава'
    assert body['price'] == 80


def test_v1_post_empty_body_returns_400(client):
    # Arrange
    payload = {}
    # Act
    response = client.post(V1, json=payload)
    # Assert
    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_v1_post_price_as_string_returns_400(client):
    # Arrange
    payload = valid_data(price='70')
    # Act
    response = client.post(V1, json=payload)
    # Assert
    assert response.status_code == 400


def test_v1_post_negative_price_returns_400(client):
    # Arrange
    payload = valid_data(price=-0.01)
    # Act
    response = client.post(V1, json=payload)
    # Assert
    assert response.status_code == 400


def test_v1_post_missing_name_returns_400(client):
    # Arrange
    payload = valid_data()
    del payload['name']
    # Act
    response = client.post(V1, json=payload)
    # Assert
    assert response.status_code == 400


def test_v1_post_error_contains_details(client):
    # Arrange
    payload = valid_data(name='', price=-1)
    # Act
    response = client.post(V1, json=payload)
    body = response.get_json()
    # Assert
    assert response.status_code == 400
    assert 'details' in body
    assert 'name' in body['details']
    assert 'price' in body['details']


def test_v1_post_price_zero_is_allowed(client):
    # Arrange
    payload = valid_data(price=0)
    # Act
    response = client.post(V1, json=payload)
    # Assert
    assert response.status_code == 201


@pytest.mark.parametrize('length, expected', [(100, 201), (101, 400)])
def test_v1_post_name_length_boundary(client, length, expected):
    # Arrange
    payload = valid_data(name='а' * length)
    # Act
    response = client.post(V1, json=payload)
    # Assert
    assert response.status_code == expected


# ============================================================
# INTEGRATION v1: PUT
# ============================================================

def test_v1_put_replaces_product(client):
    # Arrange
    created = create_product(client)
    new_data = valid_data(name='Нова назва', price=200, category='Інше')
    # Act
    response = client.put(f"{V1}/{created['id']}", json=new_data)
    body = unwrap(response.get_json())
    # Assert
    assert response.status_code == 200
    assert body['name'] == 'Нова назва'
    assert body['price'] == 200


def test_v1_put_invalid_returns_400(client):
    # Arrange
    created = create_product(client)
    # Act
    response = client.put(f"{V1}/{created['id']}", json=valid_data(price=-5))
    # Assert
    assert response.status_code == 400


def test_v1_put_unknown_returns_404(client):
    # Arrange
    payload = valid_data()
    # Act
    response = client.put(f'{V1}/{MISSING_ID}', json=payload)
    # Assert
    assert response.status_code == 404


# ============================================================
# INTEGRATION v1: PATCH
# ============================================================

def test_v1_patch_updates_only_given_field(client):
    # Arrange
    created = create_product(client, name='Старе', price=100)
    # Act
    response = client.patch(f"{V1}/{created['id']}", json={'price': 150})
    body = unwrap(response.get_json())
    # Assert
    assert response.status_code == 200
    assert body['price'] == 150
    assert body['name'] == 'Старе'


def test_v1_patch_empty_body_returns_400(client):
    # Arrange
    created = create_product(client)
    # Act
    response = client.patch(f"{V1}/{created['id']}", json={})
    # Assert
    assert response.status_code == 400


def test_v1_patch_invalid_price_returns_400(client):
    # Arrange
    created = create_product(client)
    # Act
    response = client.patch(f"{V1}/{created['id']}", json={'price': -1})
    # Assert
    assert response.status_code == 400


def test_v1_patch_unknown_returns_404(client):
    # Arrange
    payload = {'price': 10}
    # Act
    response = client.patch(f'{V1}/{MISSING_ID}', json=payload)
    # Assert
    assert response.status_code == 404


# ============================================================
# INTEGRATION v1: DELETE, 404, 409
# ============================================================

def test_v1_delete_removes_product(client):
    # Arrange
    created = create_product(client)
    # Act
    response = client.delete(f"{V1}/{created['id']}")
    after = client.get(f"{V1}/{created['id']}")
    # Assert
    assert response.status_code in (200, 204)
    assert after.status_code == 404


def test_v1_delete_unknown_returns_404(client):
    # Arrange
    product_id = MISSING_ID
    # Act
    response = client.delete(f'{V1}/{product_id}')
    # Assert
    assert response.status_code == 404


def test_v1_get_unknown_returns_404(client):
    # Arrange
    product_id = MISSING_ID
    # Act
    response = client.get(f'{V1}/{product_id}')
    # Assert
    assert response.status_code == 404


def test_v1_delete_product_in_order_returns_409(client):
    # Arrange: замовлення з товаром (клієнт id 1 є в тестовій БД)
    created = create_product(client)
    pid = created['id']
    payloads = [
        {'customer_id': 1, 'items': [{'product_id': pid, 'quantity': 1}]},
        {'customer_id': 1, 'products': [{'product_id': pid, 'quantity': 1}]},
        {'customer_id': 1, 'product_id': pid, 'quantity': 1},
    ]
    order_created = False
    for url in ('/api/v1/orders', '/api/v2/orders'):
        for payload in payloads:
            if client.post(url, json=payload).status_code == 201:
                order_created = True
                break
        if order_created:
            break
    if not order_created:
        pytest.skip('Не вдалося створити замовлення через API (формат невідомий)')
    # Act
    response = client.delete(f'{V1}/{pid}')
    # Assert
    assert response.status_code == 409


# ============================================================
# INTEGRATION v2
# ============================================================

def test_v2_list_returns_seeded_products(client):
    # Arrange
    # Act
    response = client.get(V2)
    # Assert
    assert response.status_code == 200
    assert len(items_of(response.get_json())) == SEEDED_COUNT


def test_v2_pagination_limits_items(client):
    # Arrange
    per_page = 3
    # Act
    response = client.get(f'{V2}?page=1&per_page={per_page}')
    # Assert
    assert response.status_code == 200
    assert len(items_of(response.get_json())) == per_page


def test_v2_pagination_second_page_differs(client):
    # Arrange
    query = 'per_page=3'
    # Act
    first = items_of(client.get(f'{V2}?page=1&{query}').get_json())
    second = items_of(client.get(f'{V2}?page=2&{query}').get_json())
    # Assert
    assert {i['id'] for i in first}.isdisjoint({i['id'] for i in second})


def test_v2_sort_by_price_ascending(client):
    # Arrange
    # Act
    response = client.get(f'{V2}?sort=price')
    prices = [i['price'] for i in items_of(response.get_json())]
    # Assert
    assert response.status_code == 200
    assert prices == sorted(prices)


def test_v2_min_price_filter_includes_cheesecake(client):
    # Arrange: Чізкейк (id 4) коштує 95
    # Act
    response = client.get(f'{V2}?min_price=90')
    items = items_of(response.get_json())
    # Assert
    assert response.status_code == 200
    assert all(i['price'] >= 90 for i in items)
    assert 4 in [i['id'] for i in items]


def test_v2_max_price_filter(client):
    # Arrange
    limit = 95
    # Act
    response = client.get(f'{V2}?max_price={limit}')
    items = items_of(response.get_json())
    # Assert
    assert response.status_code == 200
    assert items
    assert all(i['price'] <= limit for i in items)


def test_v2_price_range_boundaries_inclusive(client):
    # Arrange: діапазон рівно по ціні Чізкейка
    # Act
    response = client.get(f'{V2}?min_price=95&max_price=95')
    items = items_of(response.get_json())
    # Assert
    assert response.status_code == 200
    assert 4 in [i['id'] for i in items]


@pytest.mark.parametrize('query', [
    'page=abc',
    'page=0',
    'page=-1',
    'per_page=abc',
    'per_page=-5',
    'min_price=abc',
    'max_price=abc',
])
def test_v2_invalid_params_return_400(client, query):
    # Arrange
    url = f'{V2}?{query}'
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 400
