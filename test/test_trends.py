import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from src import trends
from src.searches import Searches
from src.trends import TrendsCache

CSV_CONTENT = (
    '"Trends","Search volume","Started","Ended","Trend breakdown","Explore link"\n'
    '"julia van hest","20K+","November 17, 2026","","julia van hest,jenning de boo","https://x"\n'
    '"water","20K+","November 17, 2026","","","https://y"\n'
    '"texel","10K+","November 17, 2026","","a,texel, ,b","https://z"\n'
)


class FakeClock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestTrendsCache(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "google_trends.json"
        self.clock = FakeClock()
        self.csv = MagicMock(return_value={f"csv{i}": [f"csv{i}"] for i in range(30)})
        self.rss = MagicMock(return_value={f"rss{i}": [f"rss{i}"] for i in range(10)})

    def cache(self, **kwargs) -> TrendsCache:
        return TrendsCache(
            self.path,
            "NL",
            sources=[("CSV", self.csv), ("RSS", self.rss)],
            clock=self.clock,
            **kwargs,
        )

    def test_first_refresh_uses_bulk_source_only(self):
        cache = self.cache()

        cache.refresh(20)

        self.csv.assert_called_once_with("NL")
        self.rss.assert_not_called()
        self.assertEqual(len(cache), 30)

    def test_no_fetch_while_pool_is_fresh_and_large_enough(self):
        cache = self.cache()
        cache.refresh(20)
        self.clock.advance(3 * 3600)

        cache.refresh(20)

        self.csv.assert_called_once()

    def test_pool_persists_across_instances(self):
        self.cache().refresh(20)
        self.clock.advance(60)

        second = self.cache()
        second.refresh(20)

        self.assertEqual(len(second), 30)
        self.csv.assert_called_once()

    def test_stale_pool_is_replaced(self):
        cache = self.cache()
        cache.refresh(5)
        self.csv.return_value = {"new": ["new"]}
        self.clock.advance(25 * 3600)

        cache.refresh(1)

        self.assertEqual(cache.trends, {"new": ["new"]})

    def test_stale_pool_is_kept_when_every_source_fails(self):
        cache = self.cache()
        cache.refresh(5)
        self.csv.side_effect = RuntimeError("boom")
        self.rss.side_effect = RuntimeError("boom")
        self.clock.advance(25 * 3600)

        cache.refresh(1)

        self.assertEqual(len(cache), 30)
        self.assertIsNotNone(cache.pick())

    def test_falls_back_to_rss_when_csv_fails(self):
        self.csv.side_effect = RuntimeError("chrome missing")
        cache = self.cache()

        cache.refresh(20)

        self.assertEqual(len(cache), 10)
        self.assertTrue(cache.pick()[0].startswith("rss"))

    def test_failed_attempts_are_not_retried_within_the_interval(self):
        self.csv.side_effect = RuntimeError("boom")
        self.rss.side_effect = RuntimeError("boom")
        cache = self.cache()

        cache.refresh(20)
        self.clock.advance(10 * 60)
        cache.refresh(20)
        self.assertEqual(self.csv.call_count, 1)
        self.assertEqual(self.rss.call_count, 1)

        self.clock.advance(51 * 60)
        cache.refresh(20)
        self.assertEqual(self.csv.call_count, 2)

    def test_back_off_survives_a_restart(self):
        self.csv.side_effect = RuntimeError("boom")
        self.rss.side_effect = RuntimeError("boom")
        self.cache().refresh(20)
        self.clock.advance(60)

        self.cache().refresh(20)

        self.assertEqual(self.csv.call_count, 1)

    def test_used_keywords_are_not_fed_back_by_later_fetches(self):
        self.csv.side_effect = RuntimeError("boom")
        cache = self.cache()
        cache.refresh(20)
        for keyword in list(cache.trends):
            cache.markUsed(keyword)
        self.clock.advance(2 * 3600)

        cache.refresh(1)

        self.assertEqual(len(cache), 0)
        self.assertEqual(self.rss.call_count, 2)

    def test_used_keywords_can_return_after_a_day(self):
        self.csv.return_value = {"a": ["a"], "b": ["b"]}
        cache = self.cache()
        cache.refresh(2)
        cache.markUsed("a")
        self.clock.advance(25 * 3600)

        cache.refresh(2)

        self.assertEqual(set(cache.trends), {"a", "b"})

    def test_pick_returns_a_copy_of_the_related_keywords(self):
        self.csv.return_value = {"a": ["a", "b"]}
        cache = self.cache()
        cache.refresh(1)

        keyword, related = cache.pick()
        related.pop(0)

        self.assertEqual(keyword, "a")
        self.assertEqual(cache.trends["a"], ["a", "b"])

    def test_pick_on_empty_pool_returns_none(self):
        self.assertIsNone(self.cache().pick())

    def test_corrupted_cache_file_is_ignored(self):
        self.path.write_text("not json", encoding="utf-8")

        cache = self.cache()

        self.assertEqual(len(cache), 0)
        cache.refresh(1)
        self.assertEqual(len(cache), 30)
        json.loads(self.path.read_text(encoding="utf-8"))

    def test_legacy_shelf_files_do_not_matter(self):
        (self.path.parent / "google_trends.dat").write_text("x")

        self.assertEqual(len(self.cache()), 0)


class TestSources(TestCase):
    def test_csv_source_parses_keywords_and_related_keywords(self):
        def fakeDownload(geo, hours, download_dir, output_format):
            self.assertEqual((geo, output_format), ("NL", "csv"))
            path = Path(download_dir) / "trends.csv"
            path.write_text(CSV_CONTENT, encoding="utf-8-sig")
            return str(path)

        with patch.object(trends, "download_google_trends_csv", fakeDownload):
            result = trends.fetchTrendingCsv("NL")

        self.assertEqual(
            result,
            {
                "julia van hest": ["julia van hest", "jenning de boo"],
                "water": ["water"],
                "texel": ["texel", "a", "b"],
            },
        )

    def test_csv_source_raises_when_nothing_was_downloaded(self):
        with patch.object(trends, "download_google_trends_csv", return_value=None):
            with self.assertRaises(RuntimeError):
                trends.fetchTrendingCsv("NL")

    def test_rss_source_maps_trends_to_themselves(self):
        items = [{"trend": "a"}, {"trend": ""}, {"other": 1}, {"trend": "b"}]
        with patch.object(trends, "download_google_trends_rss", return_value=items):
            self.assertEqual(
                trends.fetchTrendingRss("NL"), {"a": ["a"], "b": ["b"]}
            )


class TestSearchesWithoutTrends(TestCase):
    def test_bing_search_gives_up_when_there_are_no_keywords(self):
        with patch("src.searches.TrendsCache") as cacheClass:
            cacheClass.return_value.pick.return_value = None
            searches = Searches(MagicMock())

        self.assertFalse(searches.bingSearch())
        searches.browser.utils.goToSearch.assert_not_called()
