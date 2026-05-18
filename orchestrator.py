"""
Orchestrator v2 — 전체 파이프라인 조율 (28개 소스)

Layer 1 수집 (병렬):
  collector + intl_org_collector + kr_research_collector
  + domestic_tracker + youtube_collector

Layer 2 정제: dedup

Layer 3 분석 (Claude API):
  analyzer → paradigm_detector → minseang_analyzer

Layer 4 출력: reporter
"""
import argparse, logging, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from config import LOG_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger("orchestrator")


def safe(name, fn, *args):
    try:
        r = fn(*args)
        logger.info(f"  ✓ {name}")
        return r
    except Exception as e:
        logger.error(f"  ✗ {name}: {e}", exc_info=True)
        return None


def run(target_date: str = None):
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info(f"  이란전쟁 민생 에이전트 v2 — {target_date}")
    logger.info(f"  수원시정연구원 | 28개 소스 통합 파이프라인")
    logger.info("=" * 60)

    # ── Layer 1: 수집 (병렬)
    logger.info("[Layer 1] 수집 시작...")
    import collector, intl_org_collector, kr_research_collector

    collect_results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {
            ex.submit(collector.run, target_date):              "collector",
            ex.submit(intl_org_collector.run, target_date):     "intl_org",
            ex.submit(kr_research_collector.run, target_date):  "kr_research",
        }
        for mod_name, import_name in [
            ("domestic_tracker", "domestic_tracker"),
            ("youtube_collector", "youtube_collector"),
        ]:
            try:
                mod = __import__(import_name)
                futures[ex.submit(mod.run, target_date)] = mod_name
            except ImportError:
                logger.info(f"  {mod_name} 없음 — 건너뜀")

        for fut in as_completed(futures):
            name = futures[fut]
            result = fut.result()
            if result:
                collect_results[name] = result

    raw_path = collect_results.get("collector")
    if not raw_path:
        logger.error("collector 실패. 중단.")
        sys.exit(1)

    # ── Layer 2: 정제
    logger.info("[Layer 2] 정제...")
    import dedup
    clean_path = safe("dedup", dedup.run, raw_path)
    if not clean_path:
        sys.exit(1)

    # ── Layer 3: 분석
    logger.info("[Layer 3] Claude API 분석...")
    import analyzer
    analyzed_path = safe("analyzer", analyzer.run, clean_path)

    import paradigm_detector
    paradigm_path = safe("paradigm_detector", paradigm_detector.run, target_date)

    try:
        import country_response_tracker
        safe("country_response_tracker", country_response_tracker.run, target_date)
    except ImportError:
        logger.info("  country_response_tracker 없음")

    try:
        import minseang_analyzer
        safe("minseang_analyzer", minseang_analyzer.run, target_date)
    except ImportError:
        logger.info("  minseang_analyzer 없음")

    # ── Layer 4: 리포트
    logger.info("[Layer 4] 리포트 생성...")
    import reporter
    report_path = safe("reporter", reporter.run, analyzed_path or clean_path)

    logger.info("=" * 60)
    logger.info(f"  완료! 리포트: {report_path}")
    logger.info("=" * 60)
    return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="이란전쟁 민생 에이전트 v2")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (기본: 오늘)")
    args = parser.parse_args()
    run(args.date)
