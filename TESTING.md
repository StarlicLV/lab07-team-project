# Тестування застосунку «Кав'ярня з десертами» (лабораторна робота 07)

**Група:** ІПЗ-21

## Склад команди

| Учасник | Частина |
|---|---|
| Систалюк Артем (teamlead) | налаштування pytest (`pytest.ini`, `tests/conftest.py`, `tests/helpers.py`), unit тести `api/utils.py` і `api/errors.py` (`tests/test_utils.py`), integration тести обробки помилок (`tests/test_errors.py`), `TESTING.md`, вимірювання покриття |
| *імʼя* | товари: `tests/test_products.py` |
| *імʼя* | замовлення: `tests/test_orders.py` |
| *імʼя* | клієнти та відгуки: `tests/test_customers.py` |

## Запуск тестів

```bash
pip install -r requirements.txt
pytest                # усі тести
pytest -v             # з назвою кожного тесту
pytest --cov=app --cov=api --cov=routes --cov=models --cov-report=term-missing   # з покриттям коду
```

## Структура

```text
pytest.ini               налаштування pytest (testpaths, pythonpath)
tests/
├── conftest.py          fixtures: app (тимчасова БД) та client (тестовий клієнт Flask)
├── helpers.py           спільні допоміжні функції (assert_api_error, create_order)
├── test_utils.py        unit тести api/utils.py та api/errors.py
├── test_errors.py       integration тести обробки помилок і ізоляції БД
├── test_products.py     товари
├── test_orders.py       замовлення
├── test_customers.py    клієнти та відгуки
└── test_api.py          тести API лабораторної 5 (написані на unittest, pytest їх теж запускає)
```

## Як працює тестова база даних

Fixture `app` у `tests/conftest.py` перед кожним тестом підставляє в `app.config['DATABASE']` шлях до нового файлу
у тимчасовій директорії (`tmp_path`) і створює таблиці з тестовими даними (`models.init_db()`).
Тому кожен тест починає з однакових даних (2 клієнти, 8 товарів, 2 промокоди), тести не залежать один від одного,
а робоча база `db.sqlite` не змінюється. Це перевіряють `test_tests_use_temporary_database` та два тести `test_isolation_*`.

Усі тести написано за схемою AAA (Arrange - Act - Assert). Граничні значення й набори вхідних даних
перевіряються параметризованими тестами `@pytest.mark.parametrize`.

## Unit тести

Unit тести перевіряють окремі функції без бази даних і вебсервера.

### `tests/test_utils.py` (Систалюк Артем)

| Тест | Що перевіряє | Очікуваний результат |
|---|---|---|
| `test_check_string_trims_spaces` | прибирання пробілів по краях | `'  Олена  '` -> `'Олена'`, помилок немає |
| `test_check_string_missing_required_field` | відсутнє обовʼязкове поле (немає ключа або `None`) | повертає `None`, помилка в `errors` |
| `test_check_string_missing_optional_field_is_not_error` | відсутнє необовʼязкове поле | `None`, помилки немає |
| `test_check_string_empty_or_blank_required` | порожній рядок, пробіли, табуляція | помилка |
| `test_check_string_wrong_type` | число, булеве, список, словник замість рядка | помилка «Має бути рядком» |
| `test_check_string_max_length_boundary` | довжина 1, 99, 100, 101 при ліміті 100 | 101 символ відхиляється, решта приймається |
| `test_check_number_accepts_valid` | 0, 0.01, 95, 99.5, 1 000 000 | значення приймаються |
| `test_check_number_rejects_invalid` | від'ємні, рядки, `True`/`False`, NaN, нескінченність, список | помилка |
| `test_check_number_missing_required` / `..._optional_is_not_error` | відсутнє обовʼязкове та необовʼязкове поле | помилка лише для обовʼязкового |
| `test_check_number_custom_minimum_boundary` | мінімум 5: значення 4, 5, 6 | 4 відхиляється, 5 і 6 приймаються |
| `test_normalize_phone` | прибирання пробілів, дужок і дефісів | `'+38 (050) 111-22-33'` -> `'+380501112233'` |
| `test_check_phone_valid` | коректні номери, межі 10 і 13 цифр | номер приймається |
| `test_check_phone_invalid` | 9 цифр, 14 цифр, літери, порожній рядок | помилка |
| `test_check_phone_missing_required` | відсутній телефон | помилка |
| `test_check_email_valid` / `..._is_optional` / `..._invalid` | коректні адреси, відсутній email, адреси без `@`, домену чи з пробілом | необовʼязкове поле; некоректне значення дає помилку |
| `test_raise_if_errors_*` | порожній словник і словник з помилками | нема винятку / `ApiError` 400 з `details` |
| `test_api_error_has_default_message`, `test_api_error_custom_message_and_details` | повідомлення за замовчуванням для кодів 400, 404, 405, 409, 415, 500 і власне повідомлення | повідомлення та `details` збережено |
| `test_get_int_arg_*` | параметр запиту: типове значення, коректне значення, `abc`, 0, -3, 1.5, межі 0/1/100/101 | некоректні дають `ApiError` 400 |
| `test_get_enum_arg`, `test_get_bool_arg_*`, `test_get_float_arg_*` | допустимі значення, значення за замовчуванням, `maybe`, `nan`, `inf` | коректні приймаються, решта дає `ApiError` |
| `test_get_json_body_*` | JSON-обʼєкт, не JSON (415), зламаний JSON (400), масив / рядок / число (400) | словник або `ApiError` |

### Тести товарів, замовлень, клієнтів

TODO: кожен учасник додає сюди таблицю для свого файлу (`tests/test_products.py`, `tests/test_orders.py`, `tests/test_customers.py`).

## Integration тести

Integration тести надсилають запити до API через тестовий клієнт Flask і перевіряють код відповіді та тіло JSON.

### `tests/test_errors.py` (Систалюк Артем)

| Тест | Запит | Очікуваний код відповіді |
|---|---|---|
| `test_api_index_lists_versions` | `GET /api` | 200, перелік версій v1 і v2 |
| `test_unknown_api_path_returns_json_404` | неіснуючі адреси в `/api/...` | 404, JSON `{"error", "status"}` |
| `test_unknown_site_page_stays_html` | `GET /no-such-page` | 404, відповідь HTML, а не JSON |
| `test_wrong_method_returns_json_405` | `POST /api/v1/customers/1`, `PUT` і `PATCH /api/v1/products`, `DELETE /api/v1/orders` | 405, JSON |
| `test_post_not_json_returns_415` | POST із `text/plain` на товари, клієнтів, замовлення | 415 |
| `test_post_broken_json_returns_400` | POST зі зламаним JSON | 400 |
| `test_post_json_that_is_not_object_returns_400` | POST із масивом, рядком, числом | 400 |
| `test_validation_error_contains_details_per_field` | `POST /api/v1/customers` з `{}` | 400, `details` по полях `name`, `phone` |
| `test_huge_id_returns_400_not_500` | `GET` з id із 31 цифри (6 адрес) | 400, а не 500 |
| `test_huge_page_number_returns_400` | `?page=` із 31 цифри | 400 |
| `test_huge_id_in_delete_returns_400` | `DELETE /api/v1/products/<великий id>` | 400 |
| `test_site_pages_still_return_html` | `/`, `/menu`, `/about`, `/delivery`, `/feedback`, `/cart` | 200, HTML |
| `test_tests_use_temporary_database` | перевірка шляху до БД у тесті | файл `test.sqlite`, а не `db.sqlite` |
| `test_isolation_*` (2 тести) | тест створює клієнта, наступний тест читає список | наступний тест бачить лише початкові дані |

### Тести товарів, замовлень, клієнтів

TODO: кожен учасник додає сюди таблицю для свого файлу.

## Результати

TODO: скріншот `pytest -v` (усі тести passed) зберегти як `docs/img/lab07-pytest.png` і вставити:

```text
![Результат pytest -v](docs/img/lab07-pytest.png)
```

### Покриття коду

TODO: скріншот `pytest --cov=app --cov=api --cov=routes --cov=models --cov-report=term-missing` зберегти
як `docs/img/lab07-coverage.png` і вставити. Додати одним-двома реченнями, які ділянки не покриті й чому.

## Висновки

TODO: 3-5 речень про те, чому навчились (unit та integration тести, fixtures, тимчасова БД, параметризація, покриття) і які були складнощі.
