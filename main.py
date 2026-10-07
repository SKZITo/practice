import re
import sys
from datetime import datetime
import psycopg2
import psycopg2.extras

#Параметры подключения
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "user": "postgres",
    "password": "postgres",
    "dbname": "tourism_agency",
}

VALID_STATUSES = ('Новая', 'В обработке', 'Оплачена', 'Отменена')


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


#Валидация
def input_non_empty(prompt):
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("  [!] Поле не может быть пустым.")


def input_int(prompt, min_val=None):
    while True:
        try:
            val = int(input(prompt).strip())
            if min_val is not None and val < min_val:
                print(f"  [!] Значение должно быть >= {min_val}")
                continue
            return val
        except ValueError:
            print("  [!] Введите целое число.")


def input_float(prompt, min_val=None):
    while True:
        try:
            val = float(input(prompt).strip().replace(',', '.'))
            if min_val is not None and val < min_val:
                print(f"  [!] Значение должно быть >= {min_val}")
                continue
            return val
        except ValueError:
            print("  [!] Введите число.")


def input_date(prompt):
    while True:
        val = input(prompt).strip()
        try:
            datetime.strptime(val, '%Y-%m-%d')
            return val
        except ValueError:
            print("  [!] Неверный формат даты. Используйте ГГГГ-ММ-ДД.")


def input_email(prompt):
    while True:
        val = input(prompt).strip()
        if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', val):
            return val
        print("  [!] Неверный формат email.")


def input_phone(prompt):
    while True:
        val = input(prompt).strip()
        if re.match(r'^[\d\-\+\(\) ]{5,20}$', val):
            return val
        print("  [!] Неверный формат телефона.")


#Вывод
def print_table(rows, headers):
    if not rows:
        print("  (нет данных)")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "| " + " | ".join(f"{{:<{w}}}" for w in widths) + " |"
    print(line)
    print(fmt.format(*headers))
    print(line)
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))
    print(line)


def pause():
    input("\n  Нажмите Enter для продолжения...")


#Туристы
def view_tourists(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT tourist_id, full_name, phone, email FROM tourists ORDER BY tourist_id;")
        rows = cur.fetchall()
    print_table(rows, ["ID", "ФИО", "Телефон", "Email"])


def add_tourist(conn):
    print("\n  --- Добавление туриста ---")
    name = input_non_empty("  ФИО: ")
    phone = input_phone("  Телефон: ")
    email = input_email("  Email: ")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tourists (full_name, phone, email) VALUES (%s,%s,%s);",
                (name, phone, email)
            )
        conn.commit()
        print("  [+] Турист добавлен.")
    except psycopg2.IntegrityError as e:
        conn.rollback()
        print(f"  [!] Ошибка: {e}")


def edit_tourist(conn):
    view_tourists(conn)
    tid = input_int("\n  ID туриста для изменения: ", 1)
    with conn.cursor() as cur:
        cur.execute("SELECT full_name, phone, email FROM tourists WHERE tourist_id=%s;", (tid,))
        row = cur.fetchone()
    if not row:
        print("  [!] Турист не найден.")
        return
    print(f"  Текущие данные: {row[0]} | {row[1]} | {row[2]}")
    name = input(f"  Новое ФИО (Enter — оставить): ").strip() or row[0]
    phone = input(f"  Новый телефон (Enter — оставить): ").strip() or row[1]
    email = input(f"  Новый email (Enter — оставить): ").strip() or row[2]
    if email != row[2]:
        while not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            email = input("  [!] Неверный email, повторите: ").strip()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tourists SET full_name=%s, phone=%s, email=%s WHERE tourist_id=%s;",
                (name, phone, email, tid)
            )
        conn.commit()
        print("  [+] Данные обновлены.")
    except psycopg2.IntegrityError as e:
        conn.rollback()
        print(f"  [!] Ошибка: {e}")


def delete_tourist(conn):
    view_tourists(conn)
    tid = input_int("\n  ID туриста для удаления: ", 1)
    with conn.cursor() as cur:
        cur.execute("SELECT full_name FROM tourists WHERE tourist_id=%s;", (tid,))
        if not cur.fetchone():
            print("  [!] Турист не найден.")
            return
    if input("  Удалить? Это затронет связанные заявки (y/n): ").lower() != 'y':
        print("  Отменено.")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tourists WHERE tourist_id=%s;", (tid,))
        conn.commit()
        print("  [+] Турист удалён.")
    except psycopg2.IntegrityError as e:
        conn.rollback()
        print(f"  [!] Ошибка: {e}")


#Направления
def view_destinations(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT destination_id, country, city_resort, COALESCE(description,'') FROM destinations ORDER BY destination_id;")
        rows = cur.fetchall()
    print_table(rows, ["ID", "Страна", "Город/Курорт", "Описание"])


def add_destination(conn):
    print("\n  --- Добавление направления ---")
    country = input_non_empty("  Страна: ")
    city = input_non_empty("  Город/Курорт: ")
    desc = input("  Описание (необязательно): ").strip() or None
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO destinations (country, city_resort, description) VALUES (%s,%s,%s);",
            (country, city, desc)
        )
    conn.commit()
    print("  [+] Направление добавлено.")


#Туры
def view_tours(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT t.tour_id, d.country, d.city_resort, t.title,
                   t.start_date, t.end_date, t.price, t.seats_count
            FROM tours t
            JOIN destinations d ON t.destination_id = d.destination_id
            ORDER BY t.tour_id;
        """)
        rows = cur.fetchall()
    print_table(rows, ["ID", "Страна", "Город", "Название",
                       "Начало", "Окончание", "Цена", "Мест"])


def search_tours(conn):
    print("\n  --- Поиск и фильтрация туров ---")
    print("  (Enter — пропустить параметр)")
    country = input("  Страна: ").strip()
    city = input("  Город/Курорт: ").strip()
    max_price_s = input("  Максимальная стоимость: ").strip()
    min_seats_s = input("  Минимум мест: ").strip()

    query = """
        SELECT t.tour_id, d.country, d.city_resort, t.title,
               t.start_date, t.end_date, t.price, t.seats_count
        FROM tours t
        JOIN destinations d ON t.destination_id = d.destination_id
        WHERE 1=1
    """
    params = []
    if country:
        query += " AND d.country ILIKE %s"; params.append(f"%{country}%")
    if city:
        query += " AND d.city_resort ILIKE %s"; params.append(f"%{city}%")
    if max_price_s:
        try:
            query += " AND t.price <= %s"; params.append(float(max_price_s.replace(',', '.')))
        except ValueError:
            print("  [!] Некорректная цена, пропускаем.")
    if min_seats_s:
        try:
            query += " AND t.seats_count >= %s"; params.append(int(min_seats_s))
        except ValueError:
            print("  [!] Некорректное число мест, пропускаем.")
    query += " ORDER BY t.price;"

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    print_table(rows, ["ID", "Страна", "Город", "Название",
                       "Начало", "Окончание", "Цена", "Мест"])


def add_tour(conn):
    view_destinations(conn)
    print("\n  --- Добавление тура ---")
    dest_id = input_int("  ID направления: ", 1)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM destinations WHERE destination_id=%s;", (dest_id,))
        if not cur.fetchone():
            print("  [!] Направление не найдено.")
            return
    title = input_non_empty("  Название тура: ")
    start = input_date("  Дата начала (ГГГГ-ММ-ДД): ")
    end = input_date("  Дата окончания (ГГГГ-ММ-ДД): ")
    if end < start:
        print("  [!] Дата окончания не может быть раньше даты начала.")
        return
    price = input_float("  Стоимость: ", 0)
    seats = input_int("  Количество мест: ", 0)
    desc = input("  Описание (необязательно): ").strip() or None
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO tours (destination_id, title, start_date, end_date, price, seats_count, description)
            VALUES (%s,%s,%s,%s,%s,%s,%s);
        """, (dest_id, title, start, end, price, seats, desc))
    conn.commit()
    print("  [+] Тур добавлен.")


def edit_delete_tour(conn):
    view_tours(conn)
    tid = input_int("\n  ID тура: ", 1)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT destination_id, title, start_date, end_date, price, seats_count, description
            FROM tours WHERE tour_id=%s;
        """, (tid,))
        row = cur.fetchone()
    if not row:
        print("  [!] Тур не найден.")
        return
    print("  1. Изменить")
    print("  2. Удалить")
    choice = input("  Выбор: ").strip()
    if choice == '1':
        title = input(f"  Название (текущее: {row[1]}): ").strip() or row[1]
        start = input(f"  Дата начала (текущая: {row[2]}): ").strip() or str(row[2])
        end = input(f"  Дата окончания (текущая: {row[3]}): ").strip() or str(row[3])
        if end < start:
            print("  [!] Неверный диапазон дат.")
            return
        price_s = input(f"  Цена (текущая: {row[4]}): ").strip()
        price = float(price_s.replace(',', '.')) if price_s else float(row[4])
        if price < 0:
            print("  [!] Цена не может быть отрицательной.")
            return
        seats_s = input(f"  Мест (текущее: {row[5]}): ").strip()
        seats = int(seats_s) if seats_s else row[5]
        if seats < 0:
            print("  [!] Мест не может быть отрицательным.")
            return
        desc = input(f"  Описание (текущее: {row[6] or '—'}): ").strip() or row[6]
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tours SET title=%s, start_date=%s, end_date=%s,
                                 price=%s, seats_count=%s, description=%s
                WHERE tour_id=%s;
            """, (title, start, end, price, seats, desc, tid))
        conn.commit()
        print("  [+] Тур обновлён.")
    elif choice == '2':
        if input("  Удалить тур и все связанные заявки? (y/n): ").lower() == 'y':
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tours WHERE tour_id=%s;", (tid,))
            conn.commit()
            print("  [+] Тур удалён.")


#Заявки
def view_applications(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT a.application_id, t.full_name, tr.title, m.full_name,
                   a.created_at, a.status, COALESCE(a.extra_info,'')
            FROM applications a
            JOIN tourists t ON a.tourist_id = t.tourist_id
            JOIN tours tr ON a.tour_id = tr.tour_id
            JOIN managers m ON a.manager_id = m.manager_id
            ORDER BY a.application_id;
        """)
        rows = cur.fetchall()
    print_table(rows, ["ID", "Турист", "Тур", "Менеджер",
                       "Создана", "Статус", "Доп. инфо"])


def add_application(conn):
    print("\n  --- Добавление заявки ---")
    view_tourists(conn)
    tourist_id = input_int("\n  ID туриста: ", 1)
    view_tours(conn)
    tour_id = input_int("\n  ID тура: ", 1)
    view_managers(conn)
    manager_id = input_int("\n  ID менеджера: ", 1)

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM tourists WHERE tourist_id=%s;", (tourist_id,))
        if not cur.fetchone():
            print("  [!] Турист не найден.")
            return
        cur.execute("SELECT 1 FROM tours WHERE tour_id=%s;", (tour_id,))
        if not cur.fetchone():
            print("  [!] Тур не найден.")
            return
        cur.execute("SELECT 1 FROM managers WHERE manager_id=%s;", (manager_id,))
        if not cur.fetchone():
            print("  [!] Менеджер не найден.")
            return

    extra = input("  Дополнительная информация (необязательно): ").strip() or None
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO applications (tourist_id, tour_id, manager_id, status, extra_info)
            VALUES (%s,%s,%s,'Новая',%s);
        """, (tourist_id, tour_id, manager_id, extra))
    conn.commit()
    print("  [+] Заявка создана со статусом 'Новая'.")


def change_status(conn):
    view_applications(conn)
    aid = input_int("\n  ID заявки: ", 1)
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM applications WHERE application_id=%s;", (aid,))
        row = cur.fetchone()
    if not row:
        print("  [!] Заявка не найдена.")
        return
    print(f"  Текущий статус: {row[0]}")
    print("  1. Новая")
    print("  2. В обработке")
    print("  3. Оплачена")
    print("  4. Отменена")
    ch = input("  Новый статус: ").strip()
    mapping = {'1': 'Новая', '2': 'В обработке', '3': 'Оплачена', '4': 'Отменена'}
    if ch not in mapping:
        print("  [!] Неверный выбор.")
        return
    with conn.cursor() as cur:
        cur.execute("UPDATE applications SET status=%s WHERE application_id=%s;",
                    (mapping[ch], aid))
    conn.commit()
    print("  [+] Статус изменён.")


def delete_application(conn):
    view_applications(conn)
    aid = input_int("\n  ID заявки для удаления: ", 1)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM applications WHERE application_id=%s;", (aid,))
        if not cur.fetchone():
            print("  [!] Заявка не найдена.")
            return
    if input("  Удалить заявку? (y/n): ").lower() == 'y':
        with conn.cursor() as cur:
            cur.execute("DELETE FROM applications WHERE application_id=%s;", (aid,))
        conn.commit()
        print("  [+] Заявка удалена.")


#Менеджеры
def view_managers(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT manager_id, full_name, position, contact_info FROM managers ORDER BY manager_id;")
        rows = cur.fetchall()
    print_table(rows, ["ID", "ФИО", "Должность", "Контакты"])


def managers_menu(conn):
    while True:
        print("\n  ─── Менеджеры ───")
        print("  1. Просмотр")
        print("  2. Добавить")
        print("  3. Изменить")
        print("  4. Удалить")
        print("  0. Назад")
        ch = input("  Выбор: ").strip()
        if ch == '1':
            view_managers(conn); pause()
        elif ch == '2':
            print("\n  --- Добавление менеджера ---")
            name = input_non_empty("  ФИО: ")
            pos = input_non_empty("  Должность: ")
            contact = input_non_empty("  Контактные данные: ")
            with conn.cursor() as cur:
                cur.execute("INSERT INTO managers (full_name, position, contact_info) VALUES (%s,%s,%s);",
                            (name, pos, contact))
            conn.commit()
            print("  [+] Менеджер добавлен.")
            pause()
        elif ch == '3':
            view_managers(conn)
            mid = input_int("\n  ID менеджера: ", 1)
            with conn.cursor() as cur:
                cur.execute("SELECT full_name, position, contact_info FROM managers WHERE manager_id=%s;", (mid,))
                row = cur.fetchone()
            if not row:
                print("  [!] Не найден."); pause(); continue
            name = input(f"  ФИО ({row[0]}): ").strip() or row[0]
            pos = input(f"  Должность ({row[1]}): ").strip() or row[1]
            contact = input(f"  Контакты ({row[2]}): ").strip() or row[2]
            with conn.cursor() as cur:
                cur.execute("UPDATE managers SET full_name=%s, position=%s, contact_info=%s WHERE manager_id=%s;",
                            (name, pos, contact, mid))
            conn.commit()
            print("  [+] Обновлено.")
            pause()
        elif ch == '4':
            view_managers(conn)
            mid = input_int("\n  ID менеджера: ", 1)
            if input("  Удалить? (y/n): ").lower() == 'y':
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM managers WHERE manager_id=%s;", (mid,))
                    conn.commit()
                    print("  [+] Удалён.")
                except psycopg2.IntegrityError as e:
                    conn.rollback()
                    print(f"  [!] Ошибка: {e}")
            pause()
        elif ch == '0':
            break


#Аналитика
def analytics_menu(conn):
    while True:
        print("\n  ─── Аналитические запросы ───")
        print("  1. Общее количество туристов, туров, заявок")
        print("  2. Количество заявок по направлениям")
        print("  3. Наиболее востребованные направления (ТОП-5)")
        print("  4. Сводная информация о продажах (оплаченные)")
        print("  0. Назад")
        ch = input("  Выбор: ").strip()

        if ch == '1':
            with conn.cursor() as cur:
                cur.execute("SELECT (SELECT COUNT(*) FROM tourists), (SELECT COUNT(*) FROM tours), (SELECT COUNT(*) FROM applications);")
                t, tr, a = cur.fetchone()
            print(f"\n  Туристов: {t} | Туров: {tr} | Заявок: {a}")
            pause()

        elif ch == '2':
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.country, d.city_resort, COUNT(a.application_id)
                    FROM destinations d
                    LEFT JOIN tours t ON t.destination_id = d.destination_id
                    LEFT JOIN applications a ON a.tour_id = t.tour_id
                    GROUP BY d.destination_id, d.country, d.city_resort
                    ORDER BY COUNT(a.application_id) DESC;
                """)
                rows = cur.fetchall()
            print_table(rows, ["Страна", "Город", "Кол-во заявок"])
            pause()

        elif ch == '3':
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.country, d.city_resort, COUNT(a.application_id) AS cnt
                    FROM applications a
                    JOIN tours t ON a.tour_id = t.tour_id
                    JOIN destinations d ON t.destination_id = d.destination_id
                    GROUP BY d.destination_id, d.country, d.city_resort
                    ORDER BY cnt DESC
                    LIMIT 5;
                """)
                rows = cur.fetchall()
            print_table(rows, ["Страна", "Город", "Кол-во заявок"])
            pause()

        elif ch == '4':
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.country, d.city_resort,
                           COUNT(a.application_id) AS cnt,
                           COALESCE(SUM(t.price), 0) AS total
                    FROM applications a
                    JOIN tours t ON a.tour_id = t.tour_id
                    JOIN destinations d ON t.destination_id = d.destination_id
                    WHERE a.status = 'Оплачена'
                    GROUP BY d.destination_id, d.country, d.city_resort
                    ORDER BY total DESC;
                """)
                rows = cur.fetchall()
            print_table(rows, ["Страна", "Город", "Кол-во оплат", "Сумма"])
            pause()

        elif ch == '0':
            break


#Главное меню
def main_menu(conn):
    while True:
        print("\n" + "=" * 60)
        print(" ИНФОРМАЦИОННАЯ СИСТЕМА ТУРАГЕНТСТВА")
        print("=" * 60)
        print("  1.  Просмотр туристов")
        print("  2.  Добавление туриста")
        print("  3.  Изменение данных туриста")
        print("  4.  Удаление туриста")
        print("  5.  Просмотр направлений")
        print("  6.  Добавление направления")
        print("  7.  Просмотр и поиск туров")
        print("  8.  Добавление тура")
        print("  9.  Изменение и удаление тура")
        print("  10. Просмотр заявок")
        print("  11. Добавление заявки")
        print("  12. Изменение статуса заявки")
        print("  13. Удаление заявки")
        print("  14. Аналитические запросы")
        print("  15. Работа с менеджерами")
        print("  0.  Выход")
        print("=" * 60)

        ch = input("  Выбор: ").strip()

        try:
            if ch == '1':
                view_tourists(conn); pause()
            elif ch == '2':
                add_tourist(conn); pause()
            elif ch == '3':
                edit_tourist(conn); pause()
            elif ch == '4':
                delete_tourist(conn); pause()
            elif ch == '5':
                view_destinations(conn); pause()
            elif ch == '6':
                add_destination(conn); pause()
            elif ch == '7':
                search_tours(conn); pause()
            elif ch == '8':
                add_tour(conn); pause()
            elif ch == '9':
                edit_delete_tour(conn); pause()
            elif ch == '10':
                view_applications(conn); pause()
            elif ch == '11':
                add_application(conn); pause()
            elif ch == '12':
                change_status(conn); pause()
            elif ch == '13':
                delete_application(conn); pause()
            elif ch == '14':
                analytics_menu(conn)
            elif ch == '15':
                managers_menu(conn)
            elif ch == '0':
                print("\n  До свидания!")
                break
            else:
                print("  [!] Неверный пункт меню.")
        except psycopg2.Error as e:
            conn.rollback()
            print(f"  [!] Ошибка БД: {e}")
            pause()
        except KeyboardInterrupt:
            print("\n  Прервано пользователем.")
            break


def main():
    try:
        conn = get_connection()
    except psycopg2.OperationalError as e:
        print(f"[!] Не удалось подключиться к БД: {e}")
        print("    Проверьте параметры DB_CONFIG и запустите create_db.py")
        sys.exit(1)

    try:
        main_menu(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()