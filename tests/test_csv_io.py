"""CSV reader: flexible headers, optional product name."""

from pathlib import Path
import tempfile

from linksearch.csv_io import read_products
from linksearch.models import ProductInput


def test_read_products_two_columns_only() -> None:
    content = "Brand,SKU\nAcme,T-1\nBeta,X2\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = Path(f.name)
    try:
        rows = read_products(path)
        assert len(rows) == 2
        assert rows[0] == ProductInput(brand="Acme", sku="T-1", product_name="")
        assert rows[1] == ProductInput(brand="Beta", sku="X2", product_name="")
    finally:
        path.unlink(missing_ok=True)


def test_read_products_optional_product_column() -> None:
    content = "brand,sku,product name\nN,P1,Widget\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = Path(f.name)
    try:
        rows = read_products(path)
        assert rows[0].product_name == "Widget"
    finally:
        path.unlink(missing_ok=True)
