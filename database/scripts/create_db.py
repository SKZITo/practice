import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

#Параметры подключения
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_NAME = "tourism_agency"

def create_database():
    #Создание самой базы данных (подключаемся к служебной БД postgres)
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
    if cur.fetchone():
        print(f"[i] База '{DB_NAME}' уже существует. Удаляем...")
        cur.execute(f"DROP DATABASE {DB_NAME} CASCADE")

    cur.execute(f"CREATE DATABASE {DB_NAME} ENCODING 'UTF8'")
    print(f"[+] База данных '{DB_NAME}' создана.")

    cur.close()
    conn.close()


def create_tables():
    #Создание 5 таблиц с ключами и ограничениями целостности.
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    )
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE tourists (
            tourist_id  SERIAL PRIMARY KEY,
            full_name   VARCHAR(150) NOT NULL,
            phone       VARCHAR(20)  NOT NULL,
            email       VARCHAR(100) UNIQUE
        );
    """)

    cur.execute("""
        CREATE TABLE managers (
            manager_id   SERIAL PRIMARY KEY,
            full_name    VARCHAR(150) NOT NULL,
            position     VARCHAR(50)  NOT NULL,
            contact_info VARCHAR(100) NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE destinations (
            destination_id SERIAL PRIMARY KEY,
            country        VARCHAR(100) NOT NULL,
            city_resort    VARCHAR(100) NOT NULL,
            description    TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE tours (
            tour_id        SERIAL PRIMARY KEY,
            destination_id INT NOT NULL REFERENCES destinations(destination_id) ON DELETE CASCADE,
            title          VARCHAR(150) NOT NULL,
            start_date     DATE NOT NULL,
            end_date       DATE NOT NULL,
            price          NUMERIC(10,2) NOT NULL CHECK (price >= 0),
            seats_count    INT NOT NULL CHECK (seats_count >= 0),
            description    TEXT,
            CHECK (end_date >= start_date)
        );
    """)

    cur.execute("""
        CREATE TABLE applications (
            application_id SERIAL PRIMARY KEY,
            tourist_id     INT NOT NULL REFERENCES tourists(tourist_id) ON DELETE CASCADE,
            tour_id        INT NOT NULL REFERENCES tours(tour_id) ON DELETE CASCADE,
            manager_id     INT NOT NULL REFERENCES managers(manager_id) ON DELETE CASCADE,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status         VARCHAR(30) NOT NULL
                CHECK (status IN ('Новая','В обработке','Оплачена','Отменена')),
            extra_info     TEXT
        );
    """)

    conn.commit()
    print("[+] Таблицы созданы: tourists, managers, destinations, tours, applications.")
    cur.close()
    conn.close()


def insert_test_data():
    #Заполнение тестовыми данными.
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    )
    cur = conn.cursor()

    cur.executemany(
        "INSERT INTO destinations (country, city_resort, description) VALUES (%s,%s,%s);",
        [
            ('Россия', 'Сочи', 'Черноморское побережье, мягкий климат'),
            ('Турция', 'Анталия', 'Все включено, 5 звезд'),
            ('Египет', 'Хургада', 'Красное море, дайвинг'),
            ('Италия', 'Рим', 'Экскурсионный тур, история'),
            ('Таиланд', 'Пхукет', 'Тропический отдых'),
        ]
    )

    cur.executemany(
        "INSERT INTO managers (full_name, position, contact_info) VALUES (%s,%s,%s);",
        [
            ('Иванов Иван Иванович', 'Менеджер', '+7-900-123-45-67'),
            ('Петрова Мария Сергеевна', 'Старший менеджер', '+7-900-765-43-21'),
            ('Сидоров Пётр Алексеевич', 'Менеджер', '+7-900-555-11-22'),
        ]
    )

    cur.executemany(
        "INSERT INTO tourists (full_name, phone, email) VALUES (%s,%s,%s);",
        [
            ('Сидоров Алексей Петрович', '+7-911-111-11-11', 'sidorov@mail.ru'),
            ('Кузнецова Ольга Ивановна', '+7-922-222-22-22', 'kuznetsova@mail.ru'),
            ('Смирнов Дмитрий Олегович', '+7-933-333-33-33', 'smirnov@mail.ru'),
            ('Волкова Анна Сергеевна', '+7-944-444-44-44', 'volkova@mail.ru'),
        ]
    )

    cur.executemany("""
        INSERT INTO tours (destination_id, title, start_date, end_date, price, seats_count, description)
        VALUES (%s,%s,%s,%s,%s,%s,%s);
    """, [
        (1, 'Сочи 7 дней', '2025-06-01', '2025-06-08', 45000, 10, 'Отдых на море'),
        (2, 'Анталия все включено', '2025-07-10', '2025-07-20', 80000, 5, '5 звезд, all inclusive'),
        (3, 'Хургада дайвинг', '2025-08-05', '2025-08-15', 60000, 8, 'Дайвинг-тур'),
        (4, 'Рим классический', '2025-09-01', '2025-09-07', 95000, 12, 'Экскурсии по Риму'),
        (5, 'Пхукет релакс', '2025-10-10', '2025-10-22', 120000, 6, 'Пляжный отдых'),
    ])

    cur.executemany("""
        INSERT INTO applications (tourist_id, tour_id, manager_id, status, extra_info)
        VALUES (%s,%s,%s,%s,%s);
    """, [
        (1, 1, 1, 'Новая', 'Просил место у окна'),
        (2, 2, 2, 'В обработке', 'Уточнить наличие мест'),
        (3, 3, 1, 'Оплачена', 'Оплата картой'),
        (4, 4, 3, 'Отменена', 'Клиент передумал'),
        (1, 5, 2, 'Оплачена', 'Медовый месяц'),
    ])

    conn.commit()
    print("[+] Тестовые данные добавлены.")
    cur.close()
    conn.close()


def main():
    print("=" * 60)
    print(" СОЗДАНИЕ БАЗЫ ДАННЫХ ИС ТУРАГЕНТСТВА")
    print("=" * 60)
    create_database()
    create_tables()
    insert_test_data()
    print("=" * 60)
    print("[✓] Готово. БД создана и заполнена.")
    print("=" * 60)


if __name__ == "__main__":
    main()