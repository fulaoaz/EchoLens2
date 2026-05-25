"""Crawler module — real e-commerce + sentiment data acquisition.

Layered architecture:
- engine/   : crawl4ai facade + compliance (robots.txt, rate limit)
- adapters/ : per-site adapters (ecommerce / sentiment)
- schemas/  : Pydantic data contracts (Product/Review/Post/Order/LiveSession)
- pipeline/ : dedup / clean / align
- seed_report.py : aggregated initial profile generator
"""
