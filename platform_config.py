"""
platform_config.py

Single source of truth for per-platform settings, so search queries and
BuiltWith lookups can never accidentally cross between platforms (e.g.
running Shopify never touches Wix's queries file or Wix's BuiltWith list).
"""

PLATFORMS = {
    "Wix": {
        "queries_file": "queries_wix.txt",
        "builtwith_slug": "Wix",
    },
    "Shopify": {
        "queries_file": "queries_shopify.txt",
        "builtwith_slug": "Shopify",
    },
    "WooCommerce": {
        "queries_file": "queries_woocommerce.txt",
        "builtwith_slug": "WooCommerce",
    },
    "WordPress": {
        "queries_file": "queries_wordpress.txt",
        "builtwith_slug": "WordPress",
    },
    "PrestaShop": {
        "queries_file": "queries_prestashop.txt",
        "builtwith_slug": "PrestaShop",
    },
    "BigCommerce": {
        "queries_file": "queries_bigcommerce.txt",
        "builtwith_slug": "BigCommerce",
    },
}


def get_config(platform: str) -> dict:
    if platform not in PLATFORMS:
        raise ValueError(
            f"Unknown platform '{platform}'. Choose from: {list(PLATFORMS.keys())}"
        )
    return PLATFORMS[platform]
