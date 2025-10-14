import argparse
import sys
from pathlib import Path

from core import parse_law, delete_deleted_laws, save_json


def resolve_law_files(sources):
    """Expand the user-provided sources into concrete law files to process."""
    law_files = []
    for src in sources:
        path = Path(src).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"경로를 찾을 수 없습니다: {path}")
        if path.is_dir():
            # Include immediate .txt files inside the directory.
            for candidate in sorted(path.iterdir()):
                if candidate.is_file() and candidate.suffix.lower() == ".txt":
                    law_files.append(candidate)
        else:
            if path.suffix.lower() != ".txt":
                raise ValueError(f"지원하지 않는 파일 형식입니다 (txt 필요): {path}")
            law_files.append(path)
    if not law_files:
        raise ValueError("처리할 .txt 법령 파일이 없습니다.")
    return law_files


def process_law_file(law_path, output_dir=None):
    """Parse a law text file and persist the structured JSON."""
    law_path = Path(law_path)
    if output_dir is None:
        target_dir = law_path.parent
    else:
        target_dir = Path(output_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / f"{law_path.stem}.json"

    law_dict = parse_law(str(law_path))
    law_dict = delete_deleted_laws(law_dict)
    save_json(law_dict, str(output_path))
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="법령 텍스트(.txt)를 구조화하여 동일한 이름의 JSON 파일로 변환합니다."
    )
    parser.add_argument(
        "source",
        nargs="+",
        help="법령 텍스트 파일 또는 해당 파일들을 포함하는 디렉터리 경로",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="결과 JSON 파일을 저장할 디렉터리 (생략 시 입력 파일과 동일한 위치)",
    )

    args = parser.parse_args(argv)

    try:
        law_files = resolve_law_files(args.source)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    failed = []
    for law_file in law_files:
        try:
            output_path = process_law_file(law_file, args.output_dir)
            print(f"{law_file} → {output_path}")
        except Exception as exc:  # pylint: disable=broad-except
            failed.append((law_file, exc))
            print(f"[오류] {law_file}: {exc}", file=sys.stderr)

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
