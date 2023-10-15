# RPY indexer 1.0.1
# Copyright (C) 2023 by Coobik, https://github.com/Coobik
# All rights reserved.
# This file is part of rpy-tools, https://github.com/Coobik/rpy-tools
# and is released under the GNU General Public License v3.0
# https://github.com/Coobik/rpy-tools/blob/main/LICENSE

from argparse import ArgumentParser
import io
import os
import sys
from io import TextIOWrapper
import time
from typing import Any, Generator, List, Optional, Tuple


VERSION = "1.0.1"
URL = "https://github.com/Coobik/rpy-tools"

MODE_READ = "r"
MODE_WRITE = "w"
ENCODING_UTF_8 = "utf-8"

LABEL = "label"
LABEL_START_POS = len(LABEL)
MAIN_INDEX_LABEL = "main_index"
EXT_RPY = ".rpy"
EXT_RPY_LENGTH = len(EXT_RPY)
TAB = "    "

MAX_LABELS_PER_MENU = 20


def current_time_millis() -> int:
    return round(time.time() * 1000)


def extract_label(line: str) -> Optional[str]:
    if not line:
        return None

    if not line.startswith(LABEL):
        return None

    colon_index = line.find(":")

    if colon_index < (LABEL_START_POS + 2):
        return None

    label = line[LABEL_START_POS:colon_index]
    return label.strip()


def read_labels_from_file(file_path: str) -> List[str]:
    labels = []

    with io.open(
        file=file_path,
        mode=MODE_READ,
        encoding=ENCODING_UTF_8,
    ) as script_file:
        while True:
            line = script_file.readline()

            if not line:
                break

            label = extract_label(line)

            if label:
                labels.append(label)

    print("source:", file_path, "labels:", len(labels))
    return labels


def normalize_label(
    label: Optional[str] = None,
    default_label: Optional[str] = None,
) -> str:
    if label:
        label = label.strip()

    if not label:
        if default_label:
            return default_label

        return f"{LABEL}_{str(current_time_millis())}"

    label = label.replace(" ", "_")
    label = label.replace(":", "_")

    if label[0].isdigit():
        return f"{LABEL}_{label}"

    return label


def prepare_output_file_path_and_root_label(
    output_dir_path: str,
    file_name: str,
) -> Tuple[str, str]:
    """
    :returns: output_file_path, root_label
    """

    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)

    output_file_path = os.path.join(output_dir_path, file_name)

    root_label = file_name[:-EXT_RPY_LENGTH]
    root_label = normalize_label(label=root_label)

    if os.path.exists(output_file_path):
        file_name = f"{root_label}_{str(current_time_millis())}{EXT_RPY}"
        output_file_path = os.path.join(output_dir_path, file_name)

    return output_file_path, root_label


def write_jump_menu_to_file(
    index_file: TextIOWrapper,
    top_label: str,
    labels: List[str],
    go_back_label: Optional[str] = None,
):
    index_file.write(f"{LABEL} {top_label}:\n\n")

    if (not go_back_label) and (not labels):
        index_file.write(f"{TAB}pass\n")
        return

    index_file.write(f"{TAB}menu:\n")

    if go_back_label:
        index_file.write(f'{TAB}{TAB}"< BACK":\n')
        index_file.write(f"{TAB}{TAB}{TAB}jump {go_back_label}\n\n")

    if not labels:
        return

    for label in labels:
        index_file.write(f'{TAB}{TAB}"{label}":\n')
        index_file.write(f"{TAB}{TAB}{TAB}jump {label}\n\n")


def batch_labels(labels: List[str], batch_size: int) -> Generator[list[str], Any, None]:
    if (not batch_size) or (batch_size < 1):
        return

    if not labels:
        return

    labels_count = len(labels)

    for i in range(0, labels_count, batch_size):
        yield labels[i : min(i + batch_size, labels_count)]


def write_labels_to_file_in_batches(
    index_file: TextIOWrapper,
    root_label: str,
    labels: List[str],
    go_back_label: Optional[str] = None,
    label_page_size: int = MAX_LABELS_PER_MENU,
):
    if (not label_page_size) or (label_page_size < 1):
        label_page_size = MAX_LABELS_PER_MENU

    if (not labels) or (len(labels) <= label_page_size):
        write_jump_menu_to_file(
            index_file=index_file,
            top_label=root_label,
            labels=labels,
            go_back_label=go_back_label,
        )

        return

    batch_number = 0
    batch_top_labels = []

    # write submenus
    for labels_batch in batch_labels(labels=labels, batch_size=label_page_size):
        top_label = f"{root_label}_{batch_number}"
        batch_top_labels.append(top_label)

        write_jump_menu_to_file(
            index_file=index_file,
            top_label=top_label,
            labels=labels_batch,
            go_back_label=root_label,
        )

        batch_number += 1

    # write top menu
    write_jump_menu_to_file(
        index_file=index_file,
        top_label=root_label,
        labels=batch_top_labels,
        go_back_label=go_back_label,
    )


def write_labels_to_file(
    labels: List[str],
    output_dir_path: str,
    file_name: str,
    go_back_label: Optional[str] = None,
    label_page_size: int = MAX_LABELS_PER_MENU,
) -> Optional[str]:
    if not labels:
        return None

    output_file_path, root_label = prepare_output_file_path_and_root_label(
        output_dir_path=output_dir_path,
        file_name=file_name,
    )

    print("target:", output_file_path, "labels:", len(labels))

    with io.open(
        file=output_file_path,
        mode=MODE_WRITE,
        encoding=ENCODING_UTF_8,
    ) as index_file:
        write_labels_to_file_in_batches(
            index_file=index_file,
            root_label=root_label,
            labels=labels,
            go_back_label=go_back_label,
            label_page_size=label_page_size,
        )

    return root_label


def process_script_file(
    dir_path: str,
    file_name: str,
    output_dir_path: str,
    main_label: str,
    label_page_size: int = MAX_LABELS_PER_MENU,
) -> Tuple[Optional[str], int]:
    """
    :returns: root_label, labels_count
    """

    file_path = os.path.join(dir_path, file_name)
    labels = read_labels_from_file(file_path=file_path)

    if not labels:
        return None, 0

    output_file_name = "index_" + file_name

    root_label = write_labels_to_file(
        labels=labels,
        output_dir_path=output_dir_path,
        file_name=output_file_name,
        go_back_label=main_label,
        label_page_size=label_page_size,
    )

    return root_label, len(labels)


def create_main_index_file(
    root_labels: List[str],
    output_dir_path: str,
    main_label: str,
    label_page_size: int = MAX_LABELS_PER_MENU,
):
    if not root_labels:
        return

    output_file_name = main_label + EXT_RPY
    print("Writing main index file:", main_label)

    write_labels_to_file(
        labels=root_labels,
        output_dir_path=output_dir_path,
        file_name=output_file_name,
        label_page_size=label_page_size,
    )


def process_files(
    input_dir_path: str,
    output_dir_path: str,
    main_label: str,
    ext: Optional[str] = None,
    label_page_size: int = MAX_LABELS_PER_MENU,
) -> List[str]:
    root_labels = []
    total_labels_count = 0

    if not input_dir_path:
        return root_labels

    for dir_path, dir_names, file_names in os.walk(input_dir_path):
        for file_name in file_names:
            if ext and (not file_name.endswith(ext)):
                continue

            try:
                root_label, labels_count = process_script_file(
                    dir_path=dir_path,
                    file_name=file_name,
                    output_dir_path=output_dir_path,
                    main_label=main_label,
                    label_page_size=label_page_size,
                )

                total_labels_count += labels_count

                if root_label:
                    root_labels.append(root_label)

            except Exception as ex:
                print(
                    "Error processing file:",
                    os.path.join(dir_path, file_name),
                    str(ex),
                )

                continue

    print(
        f"\nProcessed {len(root_labels)} {ext or ''} files - total labels: {total_labels_count}"
    )

    return root_labels


def index_rpy_files(
    input_dir_path: str,
    output_dir_path: Optional[str] = None,
    main_label: Optional[str] = None,
    label_page_size: int = MAX_LABELS_PER_MENU,
):
    if input_dir_path:
        input_dir_path = input_dir_path.strip()

    if not input_dir_path:
        print("Input directory path is not defined")
        return

    if output_dir_path:
        output_dir_path = output_dir_path.strip()

    if not output_dir_path:
        output_dir_path = os.getcwd()
        print("Output directory path is not defined - using current:", output_dir_path)

    main_label = normalize_label(label=main_label, default_label=MAIN_INDEX_LABEL)

    root_labels = process_files(
        input_dir_path=input_dir_path,
        output_dir_path=output_dir_path,
        main_label=main_label,
        ext=EXT_RPY,
        label_page_size=label_page_size,
    )

    create_main_index_file(
        root_labels=root_labels,
        output_dir_path=output_dir_path,
        main_label=main_label,
        label_page_size=label_page_size,
    )


def build_argument_parser() -> ArgumentParser:
    argument_parser = ArgumentParser(
        prog="python3 rpy_indexer.py",
        description="Collect labels from .rpy files and build jump menus",
        epilog=URL,
    )

    argument_parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Input directory path",
    )

    argument_parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="[Optional] Output directory path. Default: current directory",
    )

    argument_parser.add_argument(
        "-m",
        "--main_label",
        default=MAIN_INDEX_LABEL,
        type=str,
        required=False,
        help=f"[Optional] Main label name. Default: {MAIN_INDEX_LABEL}",
    )

    argument_parser.add_argument(
        "-s",
        "--label_page_size",
        default=MAX_LABELS_PER_MENU,
        type=int,
        required=False,
        help=f"[Optional] Max labels per menu page. Default: {MAX_LABELS_PER_MENU}",
    )

    argument_parser.add_argument(
        "-v",
        "--version",
        action="version",
        help="Show version",
        version=f"RPY indexer {VERSION}",
    )

    return argument_parser


def main() -> int:
    print("\nRPY indexer")
    print(f"{URL}\n")

    argument_parser = build_argument_parser()
    args = argument_parser.parse_args()

    try:
        index_rpy_files(
            input_dir_path=args.input,
            output_dir_path=args.output,
            main_label=args.main_label,
            label_page_size=args.label_page_size,
        )

    except Exception as ex:
        print("Error indexing RPY files:", str(ex))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
