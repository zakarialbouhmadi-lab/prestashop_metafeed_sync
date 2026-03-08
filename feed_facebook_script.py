#!/usr/bin/env python3
"""
Facebook Product Feed Generator for Prestashop 8.1.7
Writes product data directly to Google Sheets
"""

import mysql.connector
import gspread
import os
from datetime import datetime
import logging

# Configuration
DB_CONFIG = {
    'host': 'marcinxkub.mysql.dhosting.pl',
    'user': 'iego9u_zak',
    'password': 'greengl@j@OU1',
    'database': 'jo3nai_p8looksy'
}

# Google Sheets configuration
GOOGLE_CREDENTIALS_FILE = './spreadsheet-service-account-key.json'
SPREADSHEET_ID = '14zTr45QT79N7GvIJ5SUyE02aVovSLKCLnZADUyLLisM'
WORKSHEET_NAME = 'Zeszyt1'

# Site configuration
SITE_URL = 'https://looksy.com.pl'
DEFAULT_CURRENCY = 'PLN'

# Logging
LOG_FILE = './log/facebook_feed.log'

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def get_db_connection():
    """Establish database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        logging.error(f"Database connection error: {e}")
        raise

def get_google_sheet():
    """Get Google Sheets worksheet"""
    try:
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        return worksheet
    except Exception as e:
        logging.error(f"Google Sheets connection error: {e}")
        raise

def get_products_from_db():
    """Get product data from Prestashop database"""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # SQL query to get product data
        query = """
        SELECT DISTINCT
            p.id_product as id,
            pl.name as title,
            pl.description_short as description,
            p.price as base_price,
            p.active as is_active,
            sa.quantity as stock_quantity,
            il.id_image,
            p.reference as sku,
            cl.name as category_name
        FROM ps_product p
        LEFT JOIN ps_product_lang pl ON p.id_product = pl.id_product AND pl.id_lang = 1
        LEFT JOIN ps_stock_available sa ON p.id_product = sa.id_product
        LEFT JOIN ps_image i ON p.id_product = i.id_product AND i.cover = 1
        LEFT JOIN ps_image_lang il ON i.id_image = il.id_image AND il.id_lang = 1
        LEFT JOIN ps_category_product cp ON p.id_product = cp.id_product
        LEFT JOIN ps_category_lang cl ON cp.id_category = cl.id_category AND cl.id_lang = 1
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

def clean_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ''
    
    import re
    # Simple HTML tag removal
    clean_text = re.sub('<.*?>', '', text)
    # Remove extra whitespace and newlines
    clean_text = ' '.join(clean_text.split())
    return clean_text

def generate_image_url(image_id, product_id):
    """Generate product image URL"""
    if not image_id:
        return f"{SITE_URL}/img/p/pl-default-large_default.jpg"
    
    # Prestashop image path logic
    image_str = str(image_id)
    path_parts = []
    
    for char in image_str:
        path_parts.append(char)
    
    path = '/'.join(path_parts)
    return f"{SITE_URL}/img/p/{path}/{image_id}-large_default.jpg"

def format_product_data(products):
    """Format product data for Google Sheets"""
    formatted_data = []
    
    # Header row
    header = [
        'id', 'title', 'description', 'link', 'image_link', 
        'price', 'availability', 'brand', 'condition', 'gtin',
        'category', 'last_updated'
    ]
    formatted_data.append(header)
    
    for product in products:
        # Clean description
        description = clean_html(product.get('description', ''))
        
        # Generate URLs
        product_link = f"{SITE_URL}/product/{product['id']}"
        image_link = generate_image_url(product.get('id_image'), product['id'])
        
        # Determine availability
        stock_qty = product.get('stock_quantity', 0) or 0
        availability = 'in stock' if stock_qty > 0 else 'out of stock'
        
        # Format price
        price = f"{float(product.get('base_price', 0)):.2f} {DEFAULT_CURRENCY}"
        
        # Format row
        row = [
            str(product['id']),
            product.get('title', '')[:150],  # Facebook limit
            description[:500],  # Truncate for readability
            product_link,
            image_link,
            price,
            availability,
            'Looksy',  # Update with your brand
            'new',
            product.get('sku', ''),
            product.get('category_name', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
        
        formatted_data.append(row)
    
    return formatted_data

def update_google_sheet(data):
    """Update Google Sheets with product data"""
    try:
        worksheet = get_google_sheet()
        
        # Clear existing data
        worksheet.clear()
        
        # Update with new data
        worksheet.update('A1', data)
        
        logging.info(f"Google Sheet updated with {len(data)-1} products")
        
    except Exception as e:
        logging.error(f"Error updating Google Sheet: {e}")
        raise

def main():
    """Main execution function"""
    setup_logging()
    
    try:
        logging.info("Starting Facebook feed generation")
        
        # Get products from database
        products = get_products_from_db()
        
        # Format data for Google Sheets
        formatted_data = format_product_data(products)
        
        # Update Google Sheet
        update_google_sheet(formatted_data)
        
        logging.info(f"Feed generation completed successfully. {len(products)} products processed.")
        
    except Exception as e:
        logging.error(f"Feed generation failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
