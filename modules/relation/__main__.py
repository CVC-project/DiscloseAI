"""Relation 모듈 CLI 진입점.

사용 예:
    python -m modules.relation init
    python -m modules.relation collect dart --corp 005930
    python -m modules.relation collect ftc
    python -m modules.relation collect filing
    python -m modules.relation collect all
    python -m modules.relation transform
    python -m modules.relation graph
    python -m modules.relation export
    python -m modules.relation run       # 전체 파이프라인
    python -m modules.relation audit     # 무결성 체크
"""

import argparse
import sys


def cmd_init(args):
    from modules.relation.storage.db import init_local_db

    init_local_db()


def cmd_collect(args):
    source = args.source
    if source == "dart":
        from modules.relation.ingest import dart

        dart.collect(corp=args.corp)
    elif source == "ftc":
        from modules.relation.ingest import ftc

        ftc.collect()
    elif source == "filing":
        from modules.relation.ingest import filing

        filing.collect()
    elif source == "all":
        from modules.relation.ingest import dart, filing, ftc

        dart.collect(corp=None)
        ftc.collect()
        filing.collect()
    else:
        raise ValueError(f"unknown source: {source}")


def cmd_transform(args):
    from modules.relation.transform import dedupe, filters, kifrs

    filters.apply()
    kifrs.apply()
    dedupe.apply()


def cmd_graph(args):
    from modules.relation.graph import build

    build.build_graph()


def cmd_export(args):
    from modules.relation.graph import export

    export.export_json()


def cmd_run(args):
    cmd_collect(argparse.Namespace(source="all", corp=None))
    cmd_transform(args)
    cmd_graph(args)
    cmd_export(args)


def cmd_audit(args):
    raise NotImplementedError("audit: Phase 2 이후 구현")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.relation",
        description="Relation 모듈 CLI (DiscloseAI)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="로컬 SQLite DB + 스키마 생성").set_defaults(
        func=cmd_init
    )

    p_collect = sub.add_parser("collect", help="원천 데이터 수집")
    p_collect.add_argument("source", choices=["dart", "ftc", "filing", "all"])
    p_collect.add_argument("--corp", help="DART 수집 시 특정 ticker (예: 005930)")
    p_collect.set_defaults(func=cmd_collect)

    sub.add_parser("transform", help="필터·K-IFRS 분류·중복 제거").set_defaults(
        func=cmd_transform
    )
    sub.add_parser("graph", help="NetworkX MultiDiGraph 구축").set_defaults(
        func=cmd_graph
    )
    sub.add_parser("export", help="graph_top50.json 생성").set_defaults(func=cmd_export)
    sub.add_parser("run", help="collect all → transform → graph → export").set_defaults(
        func=cmd_run
    )
    sub.add_parser("audit", help="무결성 체크 (도메인 검증)").set_defaults(
        func=cmd_audit
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except NotImplementedError as e:
        print(f"[미구현] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
