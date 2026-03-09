# prestashop-meta-feed

A lightweight Python script that exports active products from a **PrestaShop 8.1.7** database into a **Google Sheets** spreadsheet formatted as a **Meta (Facebook) Product Catalog feed**.

Designed to run on a schedule (e.g. via cron) so your Meta catalog stays up to date automatically.

---

## Features

- Queries PrestaShop MySQL directly — no REST API key needed
- Outputs a Meta-compatible feed: `id`, `title`, `description`, `link`, `image_link`, `price`, `availability`, `brand`, `condition`, `gtin`, `category`
- Strips HTML from descriptions automatically
- Builds correct PrestaShop image URLs from image IDs
- All credentials stored in `config.txt` — never in the source code
- Simple rotating log file under `./log/`

---

## Prerequisites

- Python 3.8+
- A PrestaShop MySQL database accessible from the machine running the script
- A Google Cloud project with the **Google Sheets API** enabled and a **service account** with editor access to the spreadsheet ([guide](https://developers.google.com/workspace/guides/create-credentials#service-account))
- A Meta Business account with a **Product Catalog** connected to the Google Sheet ([guide](https://www.facebook.com/business/help/1713977482287158))

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/prestashop-meta-feed.git
cd prestashop-meta-feed
```

### 2. Install dependencies

```bash
pip install mysql-connector-python gspread
```

### 3. Configure

```bash
cp config.txt.example config.txt
```

Edit `config.txt`:

| Key | Description |
|-----|-------------|
| `spreadsheet_feed_id` | Google Sheets ID (from the URL) |
| `feed_sheet_name` | Tab name inside the spreadsheet |
| `shop_base_url` | Your store URL, e.g. `https://yourshop.com` |
| `service_account_file` | Path to your service account JSON key |
| `db_host` | MySQL host |
| `db_name` | PrestaShop database name |
| `db_user` | MySQL username |
| `db_pass` | MySQL password |

### 4. Add your service account key

Place your Google service account JSON file at the path defined in `service_account_file`. Share the target spreadsheet with the service account email as **Editor**.

---

## Running the Script

```bash
python feed_facebook_script.py
```

Logs are written to `./log/facebook_feed.log` and mirrored to the console.

### Automate with cron

To run every day at 4:00 AM:

```bash
crontab -e
```

Add:

```
0 4 * * * /usr/bin/python3 /path/to/feed_facebook_script.py >> /path/to/log/cron.log 2>&1
```

---

## How It Works

```
MySQL (PrestaShop DB)
        │
        ▼
  get_products_from_db()     ← active products with stock, image, category
        │
        ▼
  format_product_data()      ← clean HTML, build URLs, map availability
        │
        ▼
  Google Sheets (gspread)    ← clear sheet, write header + all rows
        │
        ▼
  Meta Catalog               ← reads the sheet on its own schedule
```

### Image URL generation

PrestaShop stores images using a folder structure derived from the image ID digits. For example, image ID `1234` maps to `/img/p/1/2/3/4/1234-large_default.jpg`. The script replicates this logic automatically.

---


## License

MIT — adapt freely for your own PrestaShop + Meta Catalog setup.
