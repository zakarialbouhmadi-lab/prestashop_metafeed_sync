#!/usr/bin/env python3
"""
Facebook / Meta Product Feed Generator for PrestaShop 8.1.7
Reads product data from the PrestaShop MySQL database and writes
a formatted feed to Google Sheets for use with Meta Catalog.
"""

import configparser
import logging
import mysql.connector
import gspread
import os
import re
from datetime import datetime

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

CONFIG_FILE = './config.txt'
LOG_FILE    = './log/facebook_feed.log'

DEFAULT_CURRENCY = 'PLN'


def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
    config.read(CONFIG_FILE)
    return config['shop']


# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )


# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────

def get_db_connection(cfg):
    try:
        return mysql.connector.connect(
            host=cfg['db_host'],
            user=cfg['db_user'],
            password=cfg['db_pass'],
            database=cfg['db_name']
        )
    except mysql.connector.Error as e:
        logging.error(f"Database connection error: {e}")
        raise


def get_products_from_db(cfg):
    """Fetch all active products from the PrestaShop database"""
    connection = None
    try:
        connection = get_db_connection(cfg)
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT DISTINCT
            p.id_product                AS id,
            pl.name                     AS title,
            pl.description_short        AS description,
            p.price                     AS base_price,
            p.active                    AS is_active,
            sa.quantity                 AS stock_quantity,
            il.id_image,
            p.reference                 AS sku,
            cl.name                     AS category_name
        FROM ps_product p
        LEFT JOIN ps_product_lang pl
               ON p.id_product = pl.id_product AND pl.id_lang = 1
        LEFT JOIN ps_stock_available sa
               ON p.id_product = sa.id_product
        LEFT JOIN ps_image i
               ON p.id_product = i.id_product AND i.cover = 1
        LEFT JOIN ps_image_lang il
               ON i.id_image = il.id_image AND il.id_lang = 1
        LEFT JOIN ps_category_product cp
               ON p.id_product = cp.id_product
        LEFT JOIN ps_category_lang cl
               ON cp.id_category = cl.id_category AND cl.id_lang = 1
        WHERE p.active = 1
          AND pl.name IS NOT NULL
          AND pl.name != ''
        ORDER BY p.id_product
        """

        cursor.execute(query)
        products = cursor.fetchall()
        logging.info(f"Found {len(products)} active products")
        return products

    except Exception as e:
        logging.error(f"Error fetching products: {e}")
        raise
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


# ─────────────────────────────────────────────
# Google Sheets
# ─────────────────────────────────────────────

def get_google_sheet(cfg):
    try:
        gc = gspread.service_account(filename=cfg['service_account_file'])
        spreadsheet = gc.open_by_key(cfg['spreadsheet_feed_id'])
        return spreadsheet.worksheet(cfg['feed_sheet_name'])
    except Exception as e:
        logging.error(f"Google Sheets connection error: {e}")
        raise


def update_google_sheet(worksheet, data):
    try:
        worksheet.clear()
        worksheet.update('A1', data)
        logging.info(f"Google Sheet updated with {len(data) - 1} products")
    except Exception as e:
        logging.error(f"Error updating Google Sheet: {e}")
        raise


# ─────────────────────────────────────────────
# Data Formatting Helpers
# ─────────────────────────────────────────────

def clean_html(text):
    """Strip HTML tags and normalize whitespace"""
    if not text:
        return ''
    clean_text = re.sub('<.*?>', '', text)
    return ' '.join(clean_text.split())


def generate_image_url(site_url, image_id, product_id):
    """Build the PrestaShop image URL from an image ID"""
    if not image_id:
        return f"{site_url}/img/p/pl-default-large_default.jpg"

    path = '/'.join(str(image_id))
    return f"{site_url}/img/p/{path}/{image_id}-large_default.jpg"


def format_product_data(products, site_url):
    """Transform raw DB rows into Google Sheets rows (Meta feed format)"""
    header = [
        'id', 'title', 'description', 'link', 'image_link',
        'price', 'availability', 'brand', 'condition', 'gtin',
        'category', 'last_updated'
    ]
    rows = [header]

    for product in products:
        description  = clean_html(product.get('description', ''))
        product_link = f"{site_url}/product/{product['id']}"
        image_link   = generate_image_url(site_url, product.get('id_image'), product['id'])
        stock_qty    = product.get('stock_quantity') or 0
        availability = 'in stock' if stock_qty > 0 else 'out of stock'
        price        = f"{float(product.get('base_price', 0)):.2f} {DEFAULT_CURRENCY}"

        rows.append([
            str(product['id']),
            product.get('title', '')[:150],   # Meta title limit
            description[:500],                # Truncate for readability
            product_link,
            image_link,
            price,
            availability,
            'Looksy',
            'new',
            product.get('sku', ''),
            product.get('category_name', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])

    return rows


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

def main():
    setup_logging()
    logging.info("Starting Meta/Facebook feed generation")

    try:
        cfg      = load_config()
        products = get_products_from_db(cfg)
        data     = format_product_data(products, cfg['shop_base_url'])
        sheet    = get_google_sheet(cfg)
        update_google_sheet(sheet, data)

        logging.info(f"Feed generation completed. {len(products)} products processed.")

    except Exception as e:
        logging.error(f"Feed generation failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()