from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from database import database, products, bank
from sqlalchemy import select, update, func
import logging

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем категории товаров
CATEGORIES = [
    ("везде", "везде"),
    ("грузоподъемное оборудование", "грузоподъемное оборудование"),
    ("колесные опоры", "колесные опоры"),
    ("складская техника", "складская техника"),
    ("строительное оборудование", "строительное оборудование"),
]

@app.on_event("startup")
async def startup():
    await database.connect()
    # Создадим начальный баланс, если его нет
    query = select(bank.c.id)
    result = await database.fetch_one(query)
    if not result:
        query = bank.insert().values(money=1000.00)
        await database.execute(query)

    # Заполняем товары, если их нет (пример)
    products_to_add = [
        {"name": "Яблоки", "price_kg": 2.50, "weight": 1.0, "category": "везде"},
        {"name": "Бананы", "price_kg": 1.80, "weight": 1.0, "category": "везде"},
        {"name": "Мясо", "price_kg": 8.99, "weight": 1.0, "category": "везде"},
        {"name": "Рыба", "price_kg": 5.50, "weight": 1.0, "category": "везде"},
        {"name": "Помидоры", "price_kg": 3.10, "weight": 1.0, "category": "везде"},
        {"name": "Огурцы", "price_kg": 3.00, "weight": 1.0, "category": "везде"},
        {"name": "Шаурма", "price_kg": 18.00, "weight": 1.0, "category": "везде"},
        {"name": "Стеллаж офисный", "price_kg": 50.00, "weight": 20.0, "category": "складская техника"},
        {"name": "Шкаф офисный", "price_kg": 100.00, "weight": 40.0, "category": "складская техника"},
        {"name": "Сейф офисный", "price_kg": 200.00, "weight": 100.0, "category": "складская техника"},
        {"name": "Кран балка", "price_kg": 300.00, "weight": 150.0, "category": "грузоподъемное оборудование"},
        {"name": "Лебедка", "price_kg": 150.00, "weight": 50.0, "category": "грузоподъемное оборудование"},
        {"name": "Опора поворотная", "price_kg": 20.00, "weight": 5.0, "category": "колесные опоры"},
        {"name": "Опора неповоротная", "price_kg": 15.00, "weight": 4.0, "category": "колесные опоры"},
        {"name": "Бетономешалка", "price_kg": 250.00, "weight": 120.0, "category": "строительное оборудование"},
        {"name": "Вибратор для бетона", "price_kg": 80.00, "weight": 20.0, "category": "строительное оборудование"},
    ]
    for product_data in products_to_add:
        # Проверяем, существует ли продукт с таким именем
        query = products.select().where(products.c.name == product_data["name"])
        existing_product = await database.fetch_one(query)
        if not existing_product:
            # Если продукта нет, добавляем его
            query = products.insert().values(**product_data)
            await database.execute(query)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Роут для отображения списка товаров
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, search: str = Query(None), category: str = Query("везде")):
    # Получаем список товаров
    query = products.select()

    # Фильтруем товары по категории
    if category != "везде":
        query = products.select().where(products.c.category == category)

    # Фильтруем товары по поисковому запросу, если он есть
    if search:
        query = query.where(func.lower(products.c.name).contains(search.lower()))

    product_list = await database.fetch_all(query)

    # Получаем текущий баланс
    query = select(bank.c.money)
    balance_result = await database.fetch_one(query)
    balance = balance_result.money if balance_result else 0.0

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": product_list,
            "balance": balance,
            "search": search,
            "category": category,
            "categories": CATEGORIES,
        },
    )

# Роут для расчета цены
@app.post("/calculate_price/", response_class=HTMLResponse)
async def calculate_price(request: Request, product_name: str = Form(...), weight: float = Form(...),
                          search: str = Form(None), category: str = Form("везде")):
    # Получаем текущий баланс
    query = select(bank.c.money)
    balance_result = await database.fetch_one(query)
    balance = balance_result.money if balance_result else 0.0

    # Получаем список товаров
    query = products.select()

    # Фильтруем товары по категории
    if category != "везде":
        query = products.select().where(products.c.category == category)

    # Фильтруем товары по поисковому запросу, если он есть
    if search:
        query = query.where(func.lower(products.c.name).contains(search.lower()))

    product_list = await database.fetch_all(query)

    # Ищем товар по имени
    query = products.select().where(products.c.name == product_name)
    product = await database.fetch_one(query)

    if product:
        price = product["price_kg"] * weight
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "product_name": product_name,
                "weight": weight,
                "price": price,
                "balance": balance,
                "products": product_list,
                "search": search,
                "category": category,
                "categories": CATEGORIES,
            },
        )
    else:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Товар не найден",
                "balance": balance,
                "products": product_list,
                "search": search,
                "category": category,
                "categories": CATEGORIES,
            },
        )

# Роут для покупки товара
@app.post("/buy/", response_class=HTMLResponse)
async def buy_product(request: Request, product_name: str = Form(...), weight: float = Form(...),
                      search: str = Form(None), category: str = Form("везде")):
    logger.info(f"Начало покупки: {product_name=}, {weight=}")

    # Ищем товар
    query = products.select().where(products.c.name == product_name)
    product = await database.fetch_one(query)

    if not product:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Товар не найден",
                "search": search,
                "category": category,
                "categories": CATEGORIES,
            },
        )

    # Рассчитываем цену
    try:
        weight = float(weight)
    except ValueError:
        logger.error(f"Ошибка: Некорректный вес: {weight}")
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Некорректный вес. Введите число.",
                "search": search,
                "category": category,
                "categories": CATEGORIES,
            },
        )
    price = product["price_kg"] * weight

    # Получаем текущий баланс
    query = select(bank.c.money)
    balance_result = await database.fetch_one(query)
    balance = balance_result.money if balance_result else 0.0

    logger.info(f"Текущий баланс: {balance}, Цена: {price}")

    # Проверяем, достаточно ли денег
    if balance >= price:
        # Списываем деньги
        new_balance = balance - price
        logger.info(f"Новый баланс (после вычитания): {new_balance}")
        query = update(bank).values(money=new_balance)
        await database.execute(query)
        logger.info("Баланс успешно обновлен в БД")

        # Получаем обновленный баланс
        query = select(bank.c.money)
        balance_result = await database.fetch_one(query)
        balance = balance_result.money if balance_result else 0.0
        logger.info(f"Обновленный баланс из БД: {balance}")

        # Получаем список товаров
        query = products.select()
        # Фильтруем товары по категории
        if category != "везде":
            query = products.select().where(products.c.category == category)
        # Фильтруем товары по поисковому запросу, если он есть
        if search:
            query = query.where(func.lower(products.c.name).contains(search.lower()))

        product_list = await database.fetch_all(query)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "message": f"Покупка совершена успешно! Ваш баланс: {balance:.2f}",
                "balance": balance,
                "products": product_list,
                "search": search,
                "category": category,
                "categories": CATEGORIES,
            },
        )
    else:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Недостаточно средств для покупки.",
                "balance": balance,
                "search": search,
                "category": category,
                "categories": CATEGORIES,
            },
        )

@app.post("/cancel_last_purchase/", response_class=HTMLResponse)
async def cancel_last_purchase(request: Request, search: str = Form(None), category: str = Form("везде")):
    # Получаем текущий баланс
    query = select(bank.c.money)
    balance_result = await database.fetch_one(query)
    balance = balance_result.money if balance_result else 0.0

    # Получаем список товаров (для отображения)
    query = products.select()
    # Фильтруем товары по категории
    if category != "везде":
        query = products.select().where(products.c.category == category)
    # Фильтруем товары по поисковому запросу, если он есть
    if search:
        query = query.where(func.lower(products.c.name).contains(search.lower()))
    product_list = await database.fetch_all(query)

    # Восстанавливаем баланс (пример: возвращаем к 1000)
    initial_balance = 1000.00
    query = update(bank).values(money=initial_balance)
    await database.execute(query)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "message": "Последняя покупка отменена. Баланс восстановлен.",
            "balance": initial_balance,
            "products": product_list,
            "search": search,
            "category": category,
            "categories": CATEGORIES,
        },
    )
