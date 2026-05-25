"""Pipeline layer tests: clean / dedup / align."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.crawler.pipeline.align import align_products
from app.crawler.pipeline.clean import mask_pii, normalize_whitespace, strip_html
from app.crawler.pipeline.dedup import dedup_records

# --- mask_pii -------------------------------------------------------------

class TestMaskPII:
    def test_mask_phone(self) -> None:
        assert mask_pii("call me at 13800138000") == "call me at [PHONE]"

    def test_mask_email(self) -> None:
        out = mask_pii("contact: foo.bar+test@example.com please")
        assert out == "contact: [EMAIL] please"

    def test_mask_idcard_18(self) -> None:
        # Random-looking 18-digit string ending in X.
        out = mask_pii("身份证 11010519491231002X 已登记")
        assert out == "身份证 [IDCARD] 已登记"

    def test_mask_multiple_kinds(self) -> None:
        out = mask_pii("电话 13912345678 邮箱 a@b.cn")
        assert "[PHONE]" in out
        assert "[EMAIL]" in out
        assert "13912345678" not in out
        assert "a@b.cn" not in out

    def test_no_pii_passthrough(self) -> None:
        assert mask_pii("正常的产品描述无敏感信息") == "正常的产品描述无敏感信息"

    def test_empty_safe(self) -> None:
        assert mask_pii("") == ""

    def test_does_not_eat_normal_digits(self) -> None:
        # "138" alone is not a phone.
        assert mask_pii("已售 138 件") == "已售 138 件"


# --- strip_html ----------------------------------------------------------

class TestStripHtml:
    def test_basic_tags(self) -> None:
        assert strip_html("<p>hello <b>world</b></p>") == "hello world"

    def test_decodes_entities(self) -> None:
        assert strip_html("Tom &amp; Jerry") == "Tom & Jerry"

    def test_drops_script_body(self) -> None:
        out = strip_html("<p>ok</p><script>alert('x')</script><p>fine</p>")
        assert "alert" not in out
        assert "ok" in out and "fine" in out

    def test_drops_style_body(self) -> None:
        out = strip_html("<style>.x{color:red}</style>visible")
        assert "color:red" not in out
        assert "visible" in out

    def test_collapses_whitespace(self) -> None:
        assert strip_html("<p>a   b\n\nc</p>") == "a b c"

    def test_normalizes_nbsp(self) -> None:
        assert strip_html("a\xa0b") == "a b"


# --- normalize_whitespace ------------------------------------------------

def test_normalize_whitespace() -> None:
    assert normalize_whitespace("  hello   world\n\n!  ") == "hello world !"
    assert normalize_whitespace("") == ""


# --- dedup_records -------------------------------------------------------

class TestDedup:
    def test_dedup_by_platform_id_keeps_newer(self) -> None:
        old = {
            "platform": "jd",
            "id": "p1",
            "title": "stale title",
            "crawled_at": datetime(2026, 1, 1),
        }
        new = {
            "platform": "jd",
            "id": "p1",
            "title": "fresh title",
            "crawled_at": datetime(2026, 1, 2),
        }
        out = dedup_records([old, new])
        assert len(out) == 1
        assert out[0]["title"] == "fresh title"

    def test_dedup_by_content_fingerprint(self) -> None:
        a = {"platform": "weibo", "id": "1", "content": "保湿效果不错"}
        b = {"platform": "weibo", "id": "2", "content": "保湿效果不错"}
        out = dedup_records([a, b])
        assert len(out) == 1

    def test_keeps_distinct_records(self) -> None:
        recs = [
            {"platform": "jd", "id": "p1", "title": "A"},
            {"platform": "jd", "id": "p2", "title": "B"},
            {"platform": "taobao", "id": "p1", "title": "C"},
        ]
        out = dedup_records(recs)
        assert len(out) == 3

    def test_iso_string_timestamp(self) -> None:
        old = {
            "platform": "jd",
            "id": "p1",
            "title": "v1",
            "crawled_at": (datetime.now() - timedelta(days=1)).isoformat(),
        }
        new = {
            "platform": "jd",
            "id": "p1",
            "title": "v2",
            "crawled_at": datetime.now().isoformat(),
        }
        out = dedup_records([old, new])
        assert len(out) == 1
        assert out[0]["title"] == "v2"


# --- align_products ------------------------------------------------------

class TestAlign:
    def test_groups_same_brand_title_across_platforms(self) -> None:
        recs = [
            {"id": "jd:1", "brand": "Anker", "title": "Anker 737 移动电源 官方旗舰店"},
            {"id": "tb:9", "brand": "Anker", "title": "Anker 737 移动电源 正品"},
            {"id": "pdd:2", "brand": "Anker", "title": "Anker 737 移动电源"},
        ]
        groups = align_products(recs)
        assert len(groups) == 1
        ids = next(iter(groups.values()))
        assert sorted(ids) == ["jd:1", "pdd:2", "tb:9"]

    def test_drops_singletons(self) -> None:
        recs = [
            {"id": "jd:1", "brand": "X", "title": "独家产品"},
            {"id": "tb:9", "brand": "Y", "title": "另一种产品"},
        ]
        assert align_products(recs) == {}

    def test_skips_records_without_id(self) -> None:
        recs = [
            {"brand": "X", "title": "无id 产品"},
            {"id": "jd:1", "brand": "X", "title": "无id 产品"},
        ]
        # Only one record has an id → no group of size 2.
        assert align_products(recs) == {}

    def test_skips_empty_title(self) -> None:
        recs = [
            {"id": "jd:1", "brand": "X", "title": ""},
            {"id": "tb:9", "brand": "X", "title": ""},
        ]
        assert align_products(recs) == {}
