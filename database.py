
import os
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT") or 3306)
    )


def philippine_date():
    return datetime.now(ZoneInfo("Asia/Manila")).date()


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projectors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                availability VARCHAR(20) NOT NULL DEFAULT 'Available',
                date_borrowed DATE NULL,
                date_returned DATE NULL,
                borrowed_by VARCHAR(150) NULL
            )
        """)

        # Create the initial 10 projectors.
        for number in range(1, 11):
            cursor.execute("""
                INSERT IGNORE INTO projectors (id, name)
                VALUES (%s, %s)
            """, (number, f"Projector {number}"))

        connection.commit()

    finally:
        cursor.close()
        connection.close()


def get_projectors():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT * FROM projectors
            ORDER BY id
        """)

        projectors = cursor.fetchall()

        for projector in projectors:
            for field in ["date_borrowed", "date_returned"]:
                if projector[field]:
                    projector[field] = projector[field].isoformat()

        return projectors

    finally:
        cursor.close()
        connection.close()


def borrow_projector(projector_id, borrower):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE projectors
            SET availability = 'Not Available',
                date_borrowed = %s,
                date_returned = NULL,
                borrowed_by = %s
            WHERE id = %s
            AND availability = 'Available'
        """, (philippine_date(), borrower, projector_id))

        connection.commit()

        return cursor.rowcount > 0

    finally:
        cursor.close()
        connection.close()


def return_projector(projector_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE projectors
            SET availability = 'Available',
                date_returned = %s,
                date_borrowed = NULL,
                borrowed_by = NULL
            WHERE id = %s
            AND availability = 'Not Available'
        """, (philippine_date(), projector_id))

        connection.commit()

        return cursor.rowcount > 0

    finally:
        cursor.close()
        connection.close()


def update_projector(projector_id, name):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE projectors
            SET name = %s
            WHERE id = %s
        """, (name, projector_id))

        connection.commit()

        return cursor.rowcount > 0

    finally:
        cursor.close()
        connection.close()


def delete_projector(projector_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM projectors
            WHERE id = %s
        """, (projector_id,))

        connection.commit()

        return cursor.rowcount > 0

    finally:
        cursor.close()
        connection.close()


def save_chat(user_message, bot_response):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO chat_history (user_message, bot_response)
            VALUES (%s, %s)
        """, (user_message, bot_response))

        connection.commit()

    finally:
        cursor.close()
        connection.close()
